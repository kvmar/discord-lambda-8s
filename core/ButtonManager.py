import datetime

from core import QueueManager
from discord_lambda import Interaction
from datetime import datetime, timedelta
from dao.QueueDao import QueueDao

queue_dao = QueueDao()
def button_flow_tree(interaction: Interaction):
  if interaction.custom_id == QueueManager.join_queue_custom_id:
    join_queue_button(interaction.guild_id, interaction)
  elif interaction.custom_id == QueueManager.leave_queue_custom_id:
    leave_queue_button(interaction.guild_id, interaction)

def join_queue_button(guild_id: str, inter: Interaction):
  print("Join queue button clicked")
  resp = QueueManager.add_player(inter)

  if resp is None:
    return

  (embed, component) = resp
  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  queue_dao.put_queue(record)

  if int(datetime.utcnow().timestamp()) < record.last_updated:
    print(f"Queue message has expired: {record.last_updated}")
    record.update_last_updated()
    queue_dao.put_queue(record)
    resp = inter.edit_response(channel_id=record.channel_id, message_id=record.message_id, content=str(datetime.now()), embeds=[embed], components=[component])
    print(f'Queue message_id: {resp}')
    QueueManager.update_message_id(inter.guild_id, resp[0], resp[1])
  else:
    queue_dao.put_queue(record)
    inter.send_response(components=[component], embeds=[embed], ephemeral=False)



def leave_queue_button(guild_id: str, inter: Interaction):
  print("Leave queue button clicked")
  resp = QueueManager.remove_player(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")

  if int(datetime.utcnow().timestamp()) < record.last_updated:
    print(f"Queue message has expired: {record.last_updated}")
    record.update_last_updated()
    resp = inter.edit_response(channel_id=record.channel_id, message_id=record.message_id, content=str(datetime.now()), embeds=[embed], components=[component])
    queue_dao.put_queue(record)
    print(f'Queue message_id: {resp}')
    QueueManager.update_message_id(inter.guild_id, resp[0], resp[1])
  else:
    queue_dao.put_queue(record)
    inter.send_response(components=[component], embeds=[embed], ephemeral=False)

