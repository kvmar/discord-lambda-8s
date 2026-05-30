from core import TeamManager
from discord_lambda import CommandRegistry, Interaction, CommandArg


def team_kick(inter: Interaction, player: str) -> None:
    embed = TeamManager.kick_from_team(inter.guild_id, captain_id=inter.user_id, target_id=player)
    inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=team_kick,
        name="team_kick",
        desc="(Captain) Kick a player from your team",
        options=[CommandArg("player", "Player to kick", CommandArg.Types.USER, required=True)],
    )
