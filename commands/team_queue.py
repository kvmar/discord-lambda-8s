from core import TeamManager
from discord_lambda import CommandRegistry, Interaction


def team_queue(inter: Interaction) -> None:
    # Captain-only: puts a full team into the matchmaking pool.
    embed = TeamManager.queue_team(inter.guild_id, captain_id=inter.user_id)
    inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_queue,
        name="team_queue",
        desc="(Captain) Put your full team into the matchmaking pool",
        options=[],
    )
