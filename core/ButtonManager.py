from core import QueueManager, LeaderboardManager, TeamLeaderboardManager
from discord_lambda import Interaction
from dao.QueueDao import QueueDao

queue_dao = QueueDao()

def button_flow_tree(interaction: Interaction):
  # NOTE: "team_leaderboard_page" contains "leaderboard_page", so it must be
  # checked before the solo leaderboard page button.
  if TeamLeaderboardManager.team_leaderboard_page_custom_id in interaction.custom_id:
    team_leaderboard_page_button(interaction.guild_id, interaction)
  elif QueueManager.team_queue_join_custom_id in interaction.custom_id:
    team_pool_join_button(interaction.guild_id, interaction)
  elif QueueManager.team_queue_leave_custom_id in interaction.custom_id:
    team_pool_leave_button(interaction.guild_id, interaction)
  elif QueueManager.team_queue_start_custom_id in interaction.custom_id:
    team_pool_start_button(interaction.guild_id, interaction)
  elif LeaderboardManager.leaderboard_page_custom_id in interaction.custom_id:
    leaderboard_page_button(interaction.guild_id, interaction)
  elif QueueManager.join_waitlist_custom_id in interaction.custom_id or "join_pre_queue" in interaction.custom_id:
    join_waitlist_button(interaction.guild_id, interaction)
  elif QueueManager.leave_waitlist_custom_id in interaction.custom_id or "leave_pre_queue" in interaction.custom_id:
    leave_waitlist_button(interaction.guild_id, interaction)
  elif QueueManager.join_queue_custom_id in interaction.custom_id:
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

def leaderboard_page_button(guild_id: str, inter: Interaction):
  print(f"Leaderboard page button clicked: {inter.custom_id}")

  page = int(inter.custom_id.split("#")[1])

  embed, component = LeaderboardManager.build_leaderboard_page(guild_id, page)

  inter.send_response(embeds=[embed], components=[component], ephemeral=True)

def team_leaderboard_page_button(guild_id: str, inter: Interaction):
  print(f"Team leaderboard page button clicked: {inter.custom_id}")

  page = int(inter.custom_id.split("#")[1])

  embed, component = TeamLeaderboardManager.build_team_leaderboard_page(guild_id, page)

  inter.send_response(embeds=[embed], components=[component], ephemeral=True)

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


def join_waitlist_button(guild_id: str, inter: Interaction):
  print("Join waitlist button clicked")
  resp = QueueManager.add_waitlist_player(inter, inter.custom_id.split("#")[1])

  if resp is None:
    from discord_lambda import Embedding
    error_embed = Embedding(":x: Cannot Join Waitlist", "You can only join the waitlist when a match is ready and in progress.", color=0xFF0000)
    inter.send_followup(embeds=[error_embed], ephemeral=True)
    return

  (embed, component) = resp

  record = queue_dao.get_queue(guild_id=guild_id, queue_id=inter.custom_id.split("#")[1])
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def leave_waitlist_button(guild_id: str, inter: Interaction):
  print("Leave waitlist button clicked")
  resp = QueueManager.remove_waitlist_player(inter, inter.custom_id.split("#")[1])

  if resp is None:
    from discord_lambda import Embedding
    error_embed = Embedding(":x: Not in Waitlist", "You are not currently in the waitlist.", color=0xFF0000)
    inter.send_followup(embeds=[error_embed], ephemeral=True)
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
  QueueManager.send_match_found_dms(inter, record)
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


def team_pool_join_button(guild_id: str, inter: Interaction):
  print("Team pool Queue Up button clicked")
  queue_id = inter.custom_id.split("#")[1]
  resp = QueueManager.team_pool_join(inter, queue_id)
  if resp is None:
    return
  embed, component = resp
  record = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_id)
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def team_pool_leave_button(guild_id: str, inter: Interaction):
  print("Team pool Dequeue button clicked")
  queue_id = inter.custom_id.split("#")[1]
  resp = QueueManager.team_pool_leave(inter, queue_id)
  if resp is None:
    return
  embed, component = resp
  record = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_id)
  QueueManager.update_queue_view(record, embeds=embed, components=component, inter=inter)


def team_pool_start_button(guild_id: str, inter: Interaction):
  print("Team pool Start Match button clicked")
  queue_id = inter.custom_id.split("#")[1]
  pool_record = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_id)
  channel_id = next(iter(pool_record.channel_config), None)
  if not channel_id:
    return
  resp = QueueManager.team_pool_start(inter, queue_id, channel_id)
  if resp is None:
    return
  embed, component = resp
  pool_record = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_id)
  QueueManager.update_queue_view(pool_record, embeds=embed, components=component, inter=inter)



