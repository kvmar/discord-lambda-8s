from core import LeaderboardManager
from discord_lambda import CommandRegistry, Interaction


def leaderboard(inter: Interaction) -> None:
    print(f"Leaderboard command triggered by {inter.username} in guild {inter.guild_id}")
    embed, component = LeaderboardManager.build_leaderboard_page(inter.guild_id, 0)
    inter.send_response(embeds=[embed], components=[component], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(func=leaderboard, name="leaderboard", desc="Show the current season leaderboard", options=[])
