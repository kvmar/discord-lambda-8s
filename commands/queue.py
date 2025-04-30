from core import QueueManager
from discord_lambda import CommandRegistry, Interaction, CommandArg

def queue(inter: Interaction, queue_name: str = "1") -> None:
  print(f"Creating queue with: {queue_name} in guild_id: {inter.guild_id}")

  (embed, component) = QueueManager.create_queue_resources(inter.guild_id, queue_name)

  resp = inter.send_response(components=[component], embeds=[embed], ephemeral=False)
  print(f'Queue message_id: {resp}')
  QueueManager.update_message_id(inter.guild_id, resp[0], resp[1], queue_id=queue_name)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=queue, name="queue", desc="Adds 8s queue to discord", options=[CommandArg("queue_name", "Queue name", CommandArg.Types.STRING)])



