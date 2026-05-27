from discord_lambda import Embedding, Interaction, CommandRegistry, CommandArg, Components
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueDao
from core import QueueManager

queue_dao = QueueDao()
player_dao = PlayerDao()


def waitlist_command(interaction: Interaction, queue: str = "main") -> None:
    """Show waitlist status and allow joining/leaving"""

    response = queue_dao.get_queue(guild_id=interaction.guild_id, queue_id=queue)

    # Check if match is ready
    is_match_ready = len(response.team_1) == 4 and len(response.team_2) == 4

    if not is_match_ready:
        embed = Embedding(
            title="🕓 Waitlist",
            desc="No match in progress. Waitlist opens when a match starts.",
            color=0xFFA500
        )
        interaction.send_response(embeds=[embed], ephemeral=True)
        return

    # Build waitlist list
    waitlist_str = ""
    if len(response.waitlist) == 0:
        waitlist_str = "*No players waiting*"
    else:
        for user_id in response.waitlist:
            player_data = player_dao.get_player(response.guild_id, user_id)
            rank_emoji = player_data.get_rank_emoji()
            streak = player_data.get_streak()
            sr = int(player_data.sr)
            waitlist_str += f"{rank_emoji} {player_data.player_name}{streak} • {sr}\n"

    embed = Embedding(
        title=f"🕓 Waitlist - {queue}",
        desc=f"**Status:** Match in progress\n**Waiting:** {len(response.waitlist)}/8 players\n\n{waitlist_str}\n**Next up** when current match ends",
        color=0x00C853
    )

    # Show current match info
    team1_str = "🔵 Team 1\n"
    for user_id in response.team_1:
        player_data = player_dao.get_player(response.guild_id, user_id)
        team1_str += f"• {player_data.player_name}\n"

    team2_str = "🔴 Team 2\n"
    for user_id in response.team_2:
        player_data = player_dao.get_player(response.guild_id, user_id)
        team2_str += f"• {player_data.player_name}\n"

    embed.add_field("Current Match", f"{team1_str}\n{team2_str}", inline=False)

    # Join/Leave buttons
    component = Components()
    component.add_button("Join Pre-Queue", f"join_waitlist_custom_id#{queue}", False, 1)
    component.add_button("Leave Pre-Queue", f"leave_waitlist_custom_id#{queue}", False, 4)

    interaction.send_response(embeds=[embed], components=[component], ephemeral=True)


def setup(registry: CommandRegistry):
    registry.register_cmd(func=waitlist_command, name="waitlist", desc="Show waitlist status and join/leave", options=[CommandArg("queue", "Queue name", CommandArg.Types.STRING)])
