from core import TeamManager
from discord_lambda import CommandRegistry, Interaction


def team_leave(inter: Interaction) -> None:
    embed = TeamManager.leave_team(inter.guild_id, player_id=inter.user_id)
    inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_leave,
        name="team_leave",
        desc="Leave your current team",
        options=[],
    )
