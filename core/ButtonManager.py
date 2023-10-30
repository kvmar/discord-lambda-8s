from core import QueueManager
from discord_lambda import Interaction, Bot
from dao.QueueDao import QueueDao

queue_dao = QueueDao()
def button_flow_tree(interaction: Interaction):
  if interaction.custom_id == QueueManager.join_queue_custom_id:
    join_queue_button(interaction.guild_id, interaction)

def join_queue_button(guild_id: str, inter: Interaction):
  print("Join queue button clicked")
  (embed, component) = QueueManager.update_queue_resources(guild_id)

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  Bot.edit_message(message_id=record.message_id, channel_id=record.channel_id, guild_id=record.guild_id)