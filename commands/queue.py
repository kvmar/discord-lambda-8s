from core import QueueManager, TeamManager
from discord_lambda import CommandRegistry, Interaction, CommandArg

def queue(inter: Interaction, queue_name: str = "1") -> None:
  print(f"Creating queue with: {queue_name} in guild_id: {inter.guild_id}")

  # A queue record flagged is_team_queue renders the premade-team pool board
  # instead of the solo queue. Teams are managed via the /team_* commands.
  flagged = QueueManager.queue_dao.get_queue_or_none(inter.guild_id, queue_name)
  if flagged is not None and getattr(flagged, "is_team_queue", False):
    embed = TeamManager.build_pool_board_embed(inter.guild_id)
    inter.send_response(embeds=[embed], ephemeral=False)
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