from core import QueueManager, TeamManager, StateRepair
from discord_lambda import CommandRegistry, Interaction, CommandArg


def queue(inter: Interaction, queue_name: str = "1") -> None:
  print(f"Creating queue with: {queue_name} in guild_id: {inter.guild_id}")

  # A bracket META record can finish successfully while the originating queue's
  # OCC-protected cleanup loses a race. Repair that stale flag before deciding
  # which queue view to build so /queue never shows a completed tournament as
  # still being in progress.
  flagged, repaired, bracket_status = StateRepair.repair_stale_bracket_flag(
    inter.guild_id, queue_name
  )
  if repaired:
    print(
      f"[Queue repair] Cleared stale {bracket_status} bracket state "
      f"for queue {queue_name}."
    )

  # The results channel is for completed-match posts, not the live queue board.
  # PR #83 could recreate a missing queue-board message in any saved
  # channel_config destination, including an old results-channel entry. Clean
  # that stale destination when /queue is refreshed so future join/leave edits
  # only touch the real queue channel.
  if flagged is not None:
    flagged, removed_results_board = StateRepair.remove_result_channel_queue_board(
      flagged, inter=inter
    )
    if removed_results_board:
      print(
        f"[Queue repair] Removed stale results-channel board for {queue_name}."
      )

  if flagged is not None and getattr(flagged, "is_team_queue", False):
    embeds, components = TeamManager.build_team_pool_embed(inter.guild_id, queue_name)
    resp = inter.send_response(embeds=embeds, components=components, ephemeral=False)
    QueueManager.update_message_id(inter.guild_id, resp[0], resp[1], queue_id=queue_name)
    return

  if inter.guild_id != "1123491132765110302" and queue_name != 'HP':
    (embed, component) = QueueManager.add_player(inter.guild_id, queue_name)
  else:
    (embed, component) = QueueManager.create_queue_resources(inter.guild_id, queue_name)

  resp = inter.send_response(components=[component], embeds=[embed], ephemeral=False)
  print(f'Queue message_id: {resp}')
  QueueManager.update_message_id(inter.guild_id, resp[0], resp[1], queue_id=queue_name)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=queue, name="queue", desc="Adds 8s queue to discord", options=[CommandArg("queue_name", "Queue name", CommandArg.Types.STRING)])