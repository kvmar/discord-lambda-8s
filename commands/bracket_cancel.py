import core.BracketManager as BracketManager
from discord_lambda import CommandRegistry, Interaction, CommandArg, Embedding


def bracket_cancel(inter: Interaction, queue_name: str) -> None:
    msg = BracketManager.cancel_bracket(inter, queue_name)
    inter.send_response(
        embeds=[Embedding(desc=msg, color=0x00C853 if "check_mark" in msg else 0xFF0000)],
        ephemeral=True,
    )


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=bracket_cancel,
        name="bracket_cancel",
        desc="Cancel an active bracket tournament (admin only)",
        options=[
            CommandArg("queue_name", "Queue name the bracket is running on", CommandArg.Types.STRING, required=True)
        ]
    )
