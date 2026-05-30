from core import TeamManager
from discord_lambda import CommandRegistry, Interaction, CommandArg


def team_create(inter: Interaction, team_name: str) -> None:
    embed = TeamManager.create_team(inter.guild_id, captain_id=inter.user_id, team_name=team_name)
    inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_create,
        name="team_create",
        desc="Create a 4v4 premade team (you become captain)",
        options=[CommandArg("team_name", "Name for your team", CommandArg.Types.STRING, required=True)],
    )
