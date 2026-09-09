# ruff: noqa: F403, F405

start = """<b>Gretting(s)</b>: 

Welcome 🤗"""

BASIC_HELP_DICT = {
    "main": start,
}

def get_bot_commands():
    static_commands = {
    "Start": "Start the bot",
    "Poster": "Fetch poster links from an OTT URL",
    "Stats": "Get bot statistics",
    "Help": "Detailed help usage",
    "Ping": "Ping Bot to test Response Speed",
    "Users": "ADMINS ONLY",
    "Authorize": "ADMINS ONLY",
    "UnAuthorize": "ADMINS ONLY",
    "AddSudo": "ADMINS ONLY",
    "RmSudo": "ADMINS ONLY",
    "Broadcast": "ADMINS ONLY",
    "Log": "ADMINS ONLY",
    "BotSet": "ADMINS ONLY",
    "Restart": "ADMINS ONLY",
    }

    return static_commands.copy()


BOT_COMMANDS = get_bot_commands()


def get_help_string():
    from ..telegram_helper.bot_commands import BotCommands

    help_lines = ["NOTE: Try each command without any argument to see more details."]

    commands = BotCommands.get_commands()

    for key, cmds in commands.items():
        cmd_attr = getattr(BotCommands, f"{key}Command", None)
        if not cmd_attr:
            continue

        if isinstance(cmd_attr, list):
            cmd_str = f"/{' or /'.join(cmd_attr)}"
        else:
            cmd_str = f"/{cmd_attr}"

        if key in BOT_COMMANDS:
            help_lines.append(f"{cmd_str}: {BOT_COMMANDS[key]}")

    return "\n".join(help_lines)


help_string = get_help_string()
