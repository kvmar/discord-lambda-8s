import core.BracketManager as BracketManager
import core.StateRepair as StateRepair
from discord_lambda import CommandRegistry, Interaction, CommandArg, Embedding


def bracket_cancel(inter: Interaction, queue_name: str) -> None:
    # If the tournament already ended but the origin queue still carries the
    # bracket flag, treat this command as a repair instead of returning the
    # contradictory "already complete" error forever.
    _, repaired, bracket_status = StateRepair.repair_stale_bracket_flag(
        inter.guild_id, queue_name
    )

    if bracket_status in StateRepair.TERMINAL_BRACKET_STATUSES:
        if repaired:
            msg = (
                f":white_check_mark: Bracket was already `{bracket_status}`. "
                f"Cleared stale bracket state from queue `{queue_name}`."
            )
        else:
            msg = (
                f":warning: Bracket is already `{bracket_status}`, but its stale "
                f"queue state could not be cleared after several retries. Try again."
            )
    else:
        msg = BracketManager.cancel_bracket(inter, queue_name)

    inter.send_response(
        embeds=[Embedding(
            desc=msg,
            color=0x00C853 if ("check_mark" in msg or "warning" in msg) else 0xFF0000,
        )],
        ephemeral=False,
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
