from core import QueueManager
from discord_lambda import Interaction
from dao.QueueDao import QueueDao

queue_dao = QueueDao()

def button_flow_tree(interaction: Interaction):
  if QueueManager.join_queue_custom_id in interaction.custom_id:
    join_queue_button(interaction.guild_id, interaction)
  elif QueueManager.leave_queue_custom_id in interaction.custom_id:
    leave_queue_button(interaction.guild_id, interaction)
  elif QueueManager.start_queue_custom_id in interaction.custom_id:
    start_queue_button(interaction.guild_id, interaction, False)
  elif QueueManager.auto_pick_custom_id in interaction.custom_id:
    start_queue_button(interaction.guild_id, interaction, True)
  elif QueueManager.player_pick_custom_id in interaction.custom_id:
    player_pick_button(interaction.guild_id, interaction)
  elif QueueManager.team_1_won_custom_id in interaction.custom_id:
    team_1_won_button(interaction.guild_id, interaction)
  elif QueueManager.team_2_won_custom_id in interaction.custom_id:
    team_2_won_button(interaction.guild_id, interaction)
  elif QueueManager.cancel_match_custom_id in interaction.custom_id:
    cancel_match_button(interaction.guild_id, interaction)

def join_queue_button(guild_id: str, inter: Interaction):
  print("Join queue button clicked")
  resp = QueueManager.add_player(inter, inter.custom_id.split("#")[1])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)



def leave_queue_button(guild_id: str, inter: Interaction):
  print("Leave queue button clicked")
  resp = QueueManager.remove_player(inter, inter.custom_id.split("#")[1])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def start_queue_button(guild_id: str, inter: Interaction, autopick: bool):
  print("Start queue button clicked")
  resp = QueueManager.start_match(inter, inter.custom_id.split("#")[1], autopick)

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  record.team1_votes = list()
  record.team2_votes = list()
  record.cancel_votes = list()
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)
  if len(record.team_1) == 4 and len(record.team_2) == 4:
    print("Moving members to team queue")
  for user in record.team_1:
    print(f"Moving team 1 user: {user} to: {record.team_1_channel_id}")
    inter.move_member(guild_id=inter.guild_id, channel_id=record.team_1_channel_id, user_id=user)
  for user in record.team_2:
    print(f"Moving team 2 user: {user} to: {record.team_2_channel_id}")
    inter.move_member(guild_id=inter.guild_id, channel_id=record.team_2_channel_id, user_id=user)


def player_pick_button(guild_id, inter):
  print(f"Player pick button clicked: {inter.custom_id}")

  resp = QueueManager.player_pick(inter, inter.custom_id.split("#")[2])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[2])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)

  if len(record.team_1) == 4 and len(record.team_2) == 4:
    print("Moving members to team queue")
    for user in record.team_1:
      print(f"Moving team 1 user: {user} to: {record.team_1_channel_id}")
      inter.move_member(guild_id=inter.guild_id, channel_id=record.team_1_channel_id, user_id=user)
    for user in record.team_2:
      print(f"Moving team 2 user: {user} to: {record.team_2_channel_id}")
      inter.move_member(guild_id=inter.guild_id, channel_id=record.team_2_channel_id, user_id=user)


def team_1_won_button(guild_id: str, inter: Interaction):
  print("Team 1 Won button clicked")
  resp = QueueManager.team_1_won(inter, inter.custom_id.split("#")[1])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])

  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)

def team_2_won_button(guild_id: str, inter: Interaction):
  print("Team 2 Won button clicked")
  resp = QueueManager.team_2_won(inter, inter.custom_id.split("#")[1])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)

def cancel_match_button(guild_id: str, inter: Interaction):
  print("Cancel Match button clicked")
  resp = QueueManager.cancel_match(inter, inter.custom_id.split("#")[1])

  if resp is None:
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)



