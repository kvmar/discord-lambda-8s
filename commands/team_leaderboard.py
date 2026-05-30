from core import TeamLeaderboardManager
from discord_lambda import CommandRegistry, Interaction


def team_leaderboard(inter: Interaction) -> None:
    embed, component = TeamLeaderboardManager.build_team_leaderboard_page(inter.guild_id, 0)
    inter.send_response(embeds=[embed], components=[component], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_leaderboard,
        name="team_leaderboard",
        desc="Show the premade-team (4v4) leaderboard",
        options=[],
    )
