from core import QueueManager
from discord_lambda import Interaction
from dao.QueueDao import QueueDao

queue_dao = QueueDao()

def button_flow_tree(interaction: Interaction):
  if interaction.custom_id == QueueManager.join_queue_custom_id:
    join_queue_button(interaction.guild_id, interaction)
  elif interaction.custom_id == QueueManager.leave_queue_custom_id:
    leave_queue_button(interaction.guild_id, interaction)
  elif interaction.custom_id == QueueManager.start_queue_custom_id:
    start_queue_button(interaction.guild_id, interaction)
  elif QueueManager.player_pick_custom_id in interaction.custom_id:
    player_pick_button(interaction.guild_id, interaction)
  elif interaction.custom_id == QueueManager.team_1_won_custom_id:
    start_queue_button(interaction.guild_id, interaction)
  elif interaction.custom_id == QueueManager.team_2_won_custom_id:
    start_queue_button(interaction.guild_id, interaction)

def join_queue_button(guild_id: str, inter: Interaction):
  print("Join queue button clicked")
  resp = QueueManager.add_player(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)



def leave_queue_button(guild_id: str, inter: Interaction):
  print("Leave queue button clicked")
  resp = QueueManager.remove_player(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def start_queue_button(guild_id: str, inter: Interaction):
  print("Start queue button clicked")
  resp = QueueManager.start_match(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)

def player_pick_button(guild_id, inter):
  print(f"Player pick button clicked: {inter.custom_id}")

  resp = QueueManager.player_pick(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def team_1_won_button(guild_id: str, inter: Interaction):
  print("Team 1 Won button clicked")
  resp = QueueManager.team_1_won(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)

def team_2_won_button(guild_id: str, inter: Interaction):
  print("Team 2 Won button clicked")
  resp = QueueManager.team_2_won(inter)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id="1")
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)



