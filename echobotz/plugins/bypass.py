from pyrogram.enums import ChatType
from .. import LOGGER
from ..helper.ott import _extract_url_from_message
from ..helper.bypsr import _bp_info, _bp_links, _pack_results_html
from ..helper.utils.msg_util import send_message, edit_message
from ..helper.utils.xtra import _task
from config import Config
from echobotz.eco import echo
from ..helper.utils.btns import EchoButtons

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

def _make_hc_pack_btn(user_id, pack_id, page, max_page):
    btns = EchoButtons()
    if page > 1:
        btns.data_button("⏮ Prev", f"bpqh {user_id} {pack_id} {page-1}")
    if page < max_page:
        btns.data_button("⏭ Next", f"bpqh {user_id} {pack_id} {page+1}")
    btns.data_button("🚫 Close 🚫", f"bpqh {user_id} {pack_id} close")
    return btns.build(2)

@_task
async def _bypass_cmd(client, message):
    try:
        if message.chat.type not in (ChatType.PRIVATE, ChatType.GROUP, ChatType.SUPERGROUP):
            return
        if not getattr(message, "command", None) or not message.command:
            return
        cmd_name = message.command[0].lstrip("/").split("@")[0].lower()
        target_url = _extract_url_from_message(message)
        if not target_url:
            return await send_message(
                message,
                (
                    "<b>Usage:</b>\n"
                    f"/{cmd_name} &lt;url&gt;  <i>or</i>\n"
                    f"Reply to a URL with <code>/{cmd_name}</code>"
                ),
            )
        wait_msg = await send_message(
            message,
            f"<i>Processing:</i>\n<code>{target_url}</code>",
        )
        info, err = await _bp_info(cmd_name, target_url)
        if err:
            return await edit_message(
                wait_msg,
                f"<b>Error:</b> <code>{err}</code>",
            )
        if info.get("hc_pack") and isinstance(info.get("hc_pack_results"), list):
            user_id = message.from_user.id if message.from_user else 0
            pack_id = f"{user_id}_{id(info)}"
            _bp_user_page[pack_id] = info["hc_pack_results"]
            results = info["hc_pack_results"]
            txt, nav, page, max_page = _pack_results_html(results, page=1, per_page=10)
            btns = _make_hc_pack_btn(user_id, pack_id, 1, max_page)
            header = f"<b>✺Source:</b> { _sexy(info.get('service')) }\n<b>HubCloud Pack Results</b>\n\n{nav}\n\n"
            await edit_message(
                wait_msg,
                f"{header}{txt}\n",
                buttons=btns,
                disable_web_page_preview=True,
            )
            return
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
        links_block = _bp_links(info.get("links") or {})
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
        await edit_message(
            wait_msg,
            text,
            buttons=buttons,
        )
    except Exception as e:
        LOGGER.error(f"bypass_cmd error: {e}", exc_info=True)
        try:
            await send_message(
                message,
                "<b>Error:</b> <code>Something went wrong while bypassing the URL.</code>",
            )
        except Exception:
            pass

@_task
async def _bypass_hc_pack_cb(client, query):
    try:
        data = query.data.split()
        if len(data) != 4:
            return await query.answer()
        _, user_id, pack_id, page = data
        user_id = int(user_id)
        from_id = query.from_user.id if query.from_user else 0
        if from_id != user_id:
            return await query.answer("Not Yours!", show_alert=True)
        if page == "close":
            await query.answer()
            try:
                await query.message.delete()
            except Exception: pass
            try:
                if query.message.reply_to_message:
                    await query.message.reply_to_message.delete()
            except Exception: pass
            _bp_user_page.pop(pack_id, None)
            return
        page = int(page)
        results = _bp_user_page.get(pack_id)
        if not results:
            await query.answer("Expired", show_alert=True)
            try:
                await edit_message(query.message, "Session expired or invalid")
            except Exception:
                pass
            return
        txt, nav, curr, maxp = _pack_results_html(results, page=page, per_page=10)
        btns = _make_hc_pack_btn(user_id, pack_id, curr, maxp)
        header = f"<b>✺Source:</b> HubCloud\n<b>HubCloud Pack Results</b>\n\n{nav}\n\n"
        await edit_message(
            query.message,
            f"{header}{txt}\n",
            buttons=btns,
            disable_web_page_preview=True,
        )
        await query.answer()
    except Exception as e:
        LOGGER.error(f"hc_pack_cb error: {e}", exc_info=True)
        await query.answer("Operation failed!")
    
