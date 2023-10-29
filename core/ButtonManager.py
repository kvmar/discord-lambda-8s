from core import QueueManager
from discord_lambda import Interaction
from dao.QueueDao import QueueDao


def button_flow_tree(interaction: Interaction):
  if interaction.custom_id == QueueManager.join_queue_custom_id:
    join_queue_button(interaction.guild_id, interaction)

def join_queue_button(guild_id: str, inter: Interaction):
  print("Join queue button clicked")
  (embed, component) = QueueManager.update_queue_resources(guild_id)


  record = QueueDao.get_queue(guild_id, "1")
  inter.edit_response(components=[component], embeds=[embed], ephemeral=False, msg_id=record.message_id)