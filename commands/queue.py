from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def queue(inter: Interaction, command: str = "queue") -> None:
  embed = None
  component = None
  if command == "queue":
    (embed, component) = QueueManager.create_queue_resources(inter.guild_id)

  resp = inter.send_response(components=[component], embeds=[embed], ephemeral=False)
  print(f'Queue message_id: {resp}')
  QueueManager.update_message_id(inter.guild_id, resp[0], resp[1])


def setup(registry: CommandRegistry):
  registry.register_cmd(func=queue, name="queue", desc="Adds 8s queue to discord", options=[])



