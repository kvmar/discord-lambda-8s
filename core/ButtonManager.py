from core import QueueManager
from discord_lambda import Interaction


def button_flow_tree(interaction: Interaction):
  if interaction.custom_id == QueueManager.join_queue_custom_id:
    join_queue_button(interaction.guild_id)

def join_queue_button(guild_id: str):
  print("Join queue button clicked")
  QueueManager.update_queue_resources(guild_id)