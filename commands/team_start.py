from core import TeamManager
from discord_lambda import CommandRegistry, Interaction


def team_start(inter: Interaction) -> None:
    # Anyone can trigger matchmaking; the two closest-rated queued teams are matched.
    TeamManager.start_team_match(inter)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_start,
        name="team_start",
        desc="Match the two closest teams in the pool",
        options=[],
    )
