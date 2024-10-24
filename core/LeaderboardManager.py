from dao.LeaderboardDao import LeaderboardDao
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction
from table2ascii import table2ascii as t2a, PresetStyle


queue_dao = QueueDao()
player_dao = PlayerDao()
leaderboard_dao = LeaderboardDao()

def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")
    player_list = player_dao.get_players_by_guild_id(queue_record.guild_id)

    sorted_player_list = sorted(player_list, key=lambda x: x.elo, reverse=True)

    table = list()

    rank = 1
    for user in sorted_player_list:
        user_data = list()
        print(f"Got player: {user.player_name} with elo {user.elo}")

        user_data.append(rank)
        user_data.append(str(user.player_name + str(user.get_emoji())))
        user_data.append(str((int(user.mw) + int(user.ml))))
        user_data.append(str(int(user.mw)))
        user_data.append(str(int(user.ml)))
        user_data.append(str(int(float(user.elo) * 100)))
        user_data.append(user.delta)

        if int(user.mw) + int(user.ml) >= 10:
            table.append(user_data)
            rank = rank + 1

    # In your command:
    output = t2a(
        header=["Rank", "User", "P", "W", "L", "SR", "Change"],
        body=table,
        style=PresetStyle.thin_compact
    )

    leaderboard_record = leaderboard_dao.get_leaderboard(queue_record.guild_id)
    if len(leaderboard_record.leaderboard_message_id) > 0:
        inter.delete_message(message_id=leaderboard_record.leaderboard_message_id, channel_id=leaderboard_record.leaderboard_channel_id)
    resp = inter.send_message(content=f"```\n{output}\n```", channel_id=leaderboard_record.leaderboard_channel_id)

    # If conditional write thrown then delete message
    leaderboard_record.leaderboard_message_id = resp[0]
    leaderboard_resp = leaderboard_dao.put_leaderboard(leaderboard_record)
    if leaderboard_resp is None:
        inter.delete_message(message_id=leaderboard_record.leaderboard_message_id, channel_id=leaderboard_record.leaderboard_channel_id)







