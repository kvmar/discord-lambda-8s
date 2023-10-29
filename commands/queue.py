from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def queue(inter: Interaction, command: str = "queue") -> None:
  embed = None
  component = None
  if command == "queue":
    print(f'Queue CMD called with interaction request: {inter.data.get("guild")}')
    (embed, component) = QueueManager.create_queue_resources(inter.data.get("guild").get("id"))

  inter.send_response(components=[component], embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=queue, name="queue", desc="Adds 8s queue to discord", options=[])



