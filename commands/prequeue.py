from discord_lambda import Embedding, Interaction, CommandRegistry, CommandArg, Components
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueDao
from core import QueueManager

queue_dao = QueueDao()
player_dao = PlayerDao()


def prequeue_command(interaction: Interaction, queue_name: str = "main") -> None:
    """Show pre-queue status and allow joining/leaving"""
    interaction.defer(ephemeral=False)

    response = queue_dao.get_queue(guild_id=interaction.guild_id, queue_id=queue_name)

    # Check if match is ready
    is_match_ready = len(response.team_1) == 4 and len(response.team_2) == 4

    if not is_match_ready:
        embed = Embedding(
            title="🕓 Pre-Queue",
            desc="No match in progress. Pre-queue opens when a match starts.",
            color=0xFFA500
        )
        interaction.send_response(embeds=[embed], ephemeral=True)
        return

    # Build pre-queue list
    pre_queue_str = ""
    if len(response.pre_queue) == 0:
        pre_queue_str = "*No players waiting*"
    else:
        for user_id in response.pre_queue:
            player_data = player_dao.get_player(response.guild_id, user_id)
            rank_emoji = player_data.get_rank_emoji()
            streak = player_data.get_streak()
            sr = int(player_data.sr)
            pre_queue_str += f"{rank_emoji} {player_data.player_name}{streak} • {sr}\n"

    embed = Embedding(
        title=f"🕓 Pre-Queue - {queue_name}",
        desc=f"**Status:** Match in progress\n**Waiting:** {len(response.pre_queue)}/8 players\n\n{pre_queue_str}\n**Next up** when current match ends",
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
    component.add_button("Join Pre-Queue", f"join_pre_queue_custom_id#{queue_name}", False, 1)
    component.add_button("Leave Pre-Queue", f"leave_pre_queue_custom_id#{queue_name}", False, 4)

    interaction.send_response(embeds=[embed], components=[component], ephemeral=True)


def setup(registry: CommandRegistry) -> None:
    """Register the prequeue command"""
    registry.register_cmd(
        func=prequeue_command,
        name="prequeue",
        desc="Show pre-queue status and join/leave",
        options=[
            CommandArg(
                name="queue",
                desc="Queue name (default: main)",
                type=CommandArg.Types.STRING,
                required=False,
                choices=["main", "variant"]
            )
        ]
    )
