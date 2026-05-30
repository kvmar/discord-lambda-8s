from core import TeamManager
from discord_lambda import CommandRegistry, Interaction, CommandArg


def team_add(inter: Interaction, player: str) -> None:
    # inter.user_id = captain (caller); player = target user id (USER option)
    embed = TeamManager.add_to_team(inter.guild_id, captain_id=inter.user_id, target_id=player)
    inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_add,
        name="team_add",
        desc="(Captain) Add a player to your team",
        options=[CommandArg("player", "Player to add", CommandArg.Types.USER, required=True)],
    )
