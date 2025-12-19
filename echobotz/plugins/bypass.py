from pyrogram.enums import ChatType
from .. import LOGGER
from ..helper.ott import _extract_url_from_message
from ..helper.bypsr import _bpinfo, _bylinks, _pack_html
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.xtra import _task
from config import Config
from echobotz.eco import echo
from ..helper.utils.btns import EchoButtons

# -- User session for pack navigation
_bp_user_page = {}

def _sexy(name):
    if not name:
        return None
    name = str(name).lower()
    mapping = {
        "gdflix": "GDFlix",
        "hubcloud": "HubCloud",
        "hubdrive": "HubDrive",
        "transfer_it": "Transfer.it",
        "vcloud": "VCloud",
        "hubcdn": "HubCDN",
        "driveleech": "DriveLeech",
        "neo": "NeoLinks",
        "gdrex": "GDRex",
        "pixelcdn": "PixelCDN",
        "extraflix": "ExtraFlix",
        "extralink": "ExtraLink",
        "luxdrive": "LuxDrive",
        "nexdrive": "NexDrive",
        "hblinks": "HBLinks",
        "vegamovies": "Vegamovies",
    }
    return mapping.get(name, name.title())

def _pack_btns(uid, pid, page, maxp):
    btns = EchoButtons()
    if page > 1:
        btns.data_button("⏮ Prev", f"bpqh {uid} {pid} {page-1}")
    if page < maxp:
        btns.data_button("⏭ Next", f"bpqh {uid} {pid} {page+1}")
    btns.data_button("🚫 Close 🚫", f"bpqh {uid} {pid} close")
    return btns.build(2)

@_task
async def _bypass_cmd(client, msg):
    if msg.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
        LOGGER.info("Skip: not private/group/supergroup")
        return
    cmd_name = getattr(msg, "command", [""])[0].lstrip("/").split("@")[0].lower() if getattr(msg, "command", None) else ""
    if not cmd_name:
        LOGGER.info("Skip: command missing")
        return
    LOGGER.info(f"CMD: Triggered bypass for '{cmd_name}' by user {msg.from_user.id if msg.from_user else 'n/a'}")
    target_url = _extract_url_from_message(msg)
    if not target_url:
        await send_message(
            msg,
            (f"<b>Usage:</b>\n/{cmd_name} <url>  <i>or</i>\nReply to a URL with <code>/{cmd_name}</code>")
        )
        LOGGER.info("Skip: no url found in message")
        return
    wait_msg = await send_message(msg, f"<i>Processing:</i>\n<code>{target_url}</code>")
    info, err = await _bpinfo(cmd_name, target_url)
    if err:
        await edit_message(wait_msg, f"<b>Error:</b> <code>{err}</code>")
        LOGGER.error(f"Bypass error: {err}")
        return
    # Special pack result (HubCloud etc.)
    if info.get("hc_pack") and isinstance(info.get("hc_pack_results"), list):
        uid = msg.from_user.id if msg.from_user else 0
        pid = f"{uid}_{id(info)}"
        _bp_user_page[pid] = info["hc_pack_results"]
        results = info["hc_pack_results"]
        txt, nav, page, maxp = _pack_html(results, page=1, per_page=10)
        btns = _pack_btns(uid, pid, 1, maxp)
        header = f"<b>✺Source:</b> { _sexy(info.get('service')) }\n<b>HubCloud Pack Results</b>\n\n{nav}\n\n"
        await edit_message(wait_msg, f"{header}{txt}\n", buttons=btns, disable_web_page_preview=True)
        LOGGER.info(f"Sent pack results for user {uid}, pack {pid}")
        return
    # Common result block
    service = _sexy(info.get("service"))
    title = info.get("title")
    filesize = info.get("filesize")
    file_format = info.get("format")
    header_lines = []
    if service:
        header_lines.append(f"<b>✺Source:</b> {service}")
    if title and title != "N/A":
        if header_lines:
            header_lines.append("")
        header_lines.append("<b>File:</b>")
        header_lines.append(f"<blockquote>{title}</blockquote>")
    header_block = "\n".join(header_lines) if header_lines else ""
    meta_lines = []
    if filesize and filesize != "N/A":
        meta_lines.append(f"<b>Size:</b> {filesize}")
    if file_format and file_format != "N/A":
        meta_lines.append(f"<b>Format:</b> {file_format}")
    meta_block = ("\n".join(meta_lines) + "\n\n") if meta_lines else ""
    links_block = _bylinks(info.get("links") or {})
    text = Config.BYPASS_TEMPLATE.format(
        header_block=header_block,
        meta_block=meta_block,
        links_block=links_block,
        original_url=target_url,
    )
    btns = EchoButtons()
    btns.url_button(echo.UP_BTN, echo.UPDTE)
    btns.url_button(echo.ST_BTN, echo.REPO)
    buttons = btns.build(2)
    await edit_message(wait_msg, text, buttons=buttons)
    LOGGER.info("Bypass done and sent to user.")

@_task
async def _bypass_hc_pack_cb(client, query):
    try:
        data = query.data.split()
        if len(data) != 4:
            await query.answer()
            LOGGER.error(f"pack_cb: callback data invalid: {data}")
            return
        _, uid, pid, page = data
        uid = int(uid)
        from_id = query.from_user.id if query.from_user else 0
        if from_id != uid:
            await query.answer("Not Yours!", show_alert=True)
            LOGGER.info(f"pack_cb: forbidden callback user {from_id} for pack {pid}")
            return
        if page == "close":
            await query.answer()
            try: await query.message.delete()
            except Exception: pass
            try:
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except Exception: pass
            _bp_user_page.pop(pid, None)
            LOGGER.info(f"pack closed for {pid}")
            return
        page = int(page)
        results = _bp_user_page.get(pid)
        if not results:
            await query.answer("Expired", show_alert=True)
            await edit_message(query.message, "Session expired or invalid")
            _bp_user_page.pop(pid, None)
            LOGGER.error(f"pack_cb: expired/corrupt pack {pid}")
            return
        txt, nav, curr, maxp = _pack_html(results, page=page, per_page=10)
        btns = _pack_btns(uid, pid, curr, maxp)
        header = f"<b>✺Source:</b> HubCloud\n<b>HubCloud Pack Results</b>\n\n{nav}\n\n"
        await edit_message(query.message, f"{header}{txt}\n", buttons=btns, disable_web_page_preview=True)
        await query.answer()
        LOGGER.info(f"pack_cb: navigated pack {pid} page {page}")
    except Exception as e:
        LOGGER.error(f"hc_pack_cb error: {e}", exc_info=True)
        await query.answer("Operation failed!")
