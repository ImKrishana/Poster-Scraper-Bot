from urllib.parse import urlparse, quote_plus
import requests

from .. import LOGGER
from .utils.xtra import _sync_to_async

class EchoBypass:
    def __init__(self, key, endpoint, method="GET", norm=None):
        self.key = key
        self.endpoint = endpoint
        self.method = method
        self.norm = norm or self._norm

    async def fetch(self, url):
        api_url = self.endpoint if self.method == "POST" else f"{self.endpoint}{quote_plus(url)}"

        try:
            if self.method == "POST":
                resp = await _sync_to_async(requests.post, api_url, json={"url": url}, timeout=30)
            else:
                resp = await _sync_to_async(requests.get, api_url, timeout=30)
        except Exception:
            return None, "Failed to reach bypass service."

        if resp.status_code != 200:
            return None, "Bypass service error."

        try:
            data = resp.json()
        except Exception:
            return None, "Invalid response from bypass service."

        data = self._unwrap(data)

        if not isinstance(data, dict):
            return None, "Unexpected response from bypass service."

        if data.get("success") is False:
            return None, data.get("message") or "Bypass failed."

        return self.norm(data)

    def _unwrap(self, data):
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            if not data:
                return {}
            if len(data) == 1 and isinstance(data[0], dict):
                return data[0]
            return {"results": data, "pack": True}
        return {}

    def _norm(self, data):
        if data.get("pack") and isinstance(data.get("results"), list):
            return {
                "hc_pack": True,
                "hc_pack_results": data["results"],
                "total_files": len(data["results"]),
                "service": self.key
            }, None

        root = data.get("final") or data
        title = root.get("title") or root.get("file_name") or root.get("fileName") or "N/A"
        size = root.get("filesize") or root.get("file_size") or "N/A"
        fmt = root.get("format") or root.get("file_format") or "N/A"
        links = _xlnk(root)

        if not links:
            return None, "No direct links found."

        return {
            "title": str(title),
            "filesize": str(size),
            "format": str(fmt),
            "links": links,
            "service": self.key
        }, None

def _xlnk(root):
    out = {}
    raw = root.get("links")

    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, str) and v.startswith(("http://", "https://")):
                out[_clean(k)] = v
            elif isinstance(v, dict):
                u = v.get("url") or v.get("link")
                if isinstance(u, str) and u.startswith(("http://", "https://")):
                    out[_clean(k)] = u

    elif isinstance(raw, list):
        for i in raw:
            if not isinstance(i, dict):
                continue
            u = i.get("url") or i.get("link")
            n = i.get("type") or i.get("name") or "Link"
            if isinstance(u, str) and u.startswith(("http://", "https://")):
                out[_clean(n)] = u

    return out

def _clean(s):
    return str(s).replace("_", " ").replace("Link", "").strip().title() or "Link"

EchoByRegistry = {
    "gdflix": EchoBypass("gdflix", "https://hgbots.vercel.app/bypaas/gd.php?url="),
    "hubdrive": EchoBypass("hubdrive", "https://hgbots.vercel.app/bypaas/hubdrive.php?url="),
    "extraflix": EchoBypass("extraflix", "https://pbx1botapi.vercel.app/api/extraflix?url="),
    "hubcloud": EchoBypass("hubcloud", "https://pbx1botapi.vercel.app/api/hubcloud?url="),
    "vcloud": EchoBypass("vcloud", "https://pbx1botapi.vercel.app/api/vcloud?url="),
    "hubcdn": EchoBypass("hubcdn", "https://pbx1botapi.vercel.app/api/hubcdn?url="),
    "driveleech": EchoBypass("driveleech", "https://pbx1botapi.vercel.app/api/driveleech?url="),
    "neo": EchoBypass("neo", "https://pbx1botapi.vercel.app/api/neo?url="),
    "gdrex": EchoBypass("gdrex", "https://pbx1botapi.vercel.app/api/gdrex?url="),
    "pixelcdn": EchoBypass("pixelcdn", "https://pbx1botapi.vercel.app/api/pixelcdn?url="),
    "extralink": EchoBypass("extralink", "https://pbx1botapi.vercel.app/api/extralink?url="),
    "luxdrive": EchoBypass("luxdrive", "https://pbx1botapi.vercel.app/api/luxdrive?url="),
    "nexdrive": EchoBypass("nexdrive", "https://pbx1botsapi2.vercel.app/api/nexdrive?url="),
    "transfer_it": EchoBypass("transfer_it", "https://transfer-it-henna.vercel.app/post", method="POST"),
    "hblinks": EchoBypass("hblinks", "https://pbx1botsapi2.vercel.app/api/hblinks?url="),
    "vegamovies": EchoBypass("vegamovies", "https://pbx1botsapi2.vercel.app/api/vega?url="),
}

CMD_TO_KEY = {
    a: k
    for k, v in {
        "gdflix": ["gdflix", "gdf"],
        "hubdrive": ["hubdrive", "hd"],
        "extraflix": ["extraflix"],
        "hubcloud": ["hubcloud", "hc"],
        "vcloud": ["vcloud", "vc"],
        "hubcdn": ["hubcdn", "hcdn"],
        "driveleech": ["driveleech", "dleech"],
        "neo": ["neo", "neolinks"],
        "gdrex": ["gdrex", "gdex"],
        "pixelcdn": ["pixelcdn", "pcdn"],
        "extralink": ["extralink"],
        "luxdrive": ["luxdrive"],
        "nexdrive": ["nexdrive", "nd"],
        "transfer_it": ["transfer_it", "ti"],
        "hblinks": ["hblinks", "hbl"],
        "vegamovies": ["vegamovies", "vega"],
    }.items()
    for a in v
}

def _bysrv(cmd):
    return EchoByRegistry.get(CMD_TO_KEY.get(str(cmd).lower().lstrip("/")))

async def _bpinfo(cmd_name, target_url):
    srv = _bysrv(cmd_name)
    if not srv:
        return None, "Unknown platform."
    try:
        p = urlparse(target_url)
        if not p.scheme or not p.netloc:
            return None, "Invalid URL."
    except Exception:
        return None, "Invalid URL."
    return await srv.fetch(target_url)

def _bylinks(links):
    if not isinstance(links, dict) or not links:
        return "╰╴ No direct links found."

    grouped = any("|" in str(k) for k in links)
    out = []

    if not grouped:
        items = [
            (str(k).strip() or "Link", v.strip())
            for k, v in links.items()
            if isinstance(v, str) and v.strip().startswith(("http://", "https://"))
        ]
        for i, (k, v) in enumerate(items):
            out.append(
                f'{"╰╴" if i == len(items)-1 else "╞╴"} <b>{k}:</b> <a href="{v}">Click Here</a>'
            )
        return "\n".join(out) if out else "╰╴ No direct links found."

    groups = {}
    for k, v in links.items():
        if not isinstance(v, str):
            continue
        u = v.strip()
        if not u.startswith(("http://", "https://")):
            continue
        a, b = str(k).split("|", 1)
        groups.setdefault(a.strip(), []).append((b.strip(), u))

    for g, items in groups.items():
        out.append(f"\n<b>{g}</b>")
        for i, (k, v) in enumerate(items):
            out.append(
                f'{"╰╴" if i == len(items)-1 else "╞╴"} <b>{k}:</b> <a href="{v}">Click Here</a>'
            )

    return "\n".join(out).strip()

def _pack_html(results, page=1, per_page=10):
    total = len(results)
    max_page = (total - 1) // per_page + 1
    page = max(1, min(page, max_page))

    start = (page - 1) * per_page
    end = min(total, page * per_page)

    out = []
    for i, item in enumerate(results[start:end], start=1 + start):
        name = item.get("file_name") or "File"
        sz = item.get("file_size") or "N/A"
        out.append(f"<b>{i}. {name}</b> <code>({sz})</code>")

        links = item.get("links") or []
        for li in links:
            typ = li.get("type") or "Link"
            url = li.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                continue
            out.append(f'   ╞ <b>{typ}</b>: <a href="{url}">Click Here</a>')
        out.append("")

    txt = "\n".join(out).strip()
    nav = f"<b>Page: {page}/{max_page}</b> | <b>Total Files: {total}</b>"
    return txt, nav, page, max_page
