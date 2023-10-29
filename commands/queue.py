from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def queue(inter: Interaction, command: str = "queue") -> None:
  embed = None
  if command == "queue":
    embed = QueueManager.create_queue()

  inter.send_response(embeds=[embed])


def setup(registry: CommandRegistry):
  registry.register_cmd(func=queue, name="queue", desc="Adds 8s queue to discord.", options=[])



