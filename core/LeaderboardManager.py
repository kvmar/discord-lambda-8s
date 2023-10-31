import pandas as pd

from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction
import dataframe_image as dfi


queue_dao = QueueDao()
player_data = PlayerDao()

def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")
    player_list = player_data.get_players_by_guild_id(queue_record.guild_id)

    sorted_player_list = sorted(player_list, key=lambda x: x.elo, reverse=True)

    table = list()

    rank = 1
    for user in sorted_player_list:
        user_data = list()
        print(f"Got player: {user.player_name} with elo {user.elo}")

        user_data.append(rank)
        user_data.append(user.player_name)
        user_data.append(str((int(user.mw) + int(user.ml))))
        user_data.append(str(int(user.mw)))
        user_data.append(str(int(user.ml)))
        user_data.append(str(int(float(user.elo) * 100)))
        user_data.append(user.delta)

        if int(user.mw) + int(user.ml) >= 2:
            table.append(user_data)
            rank = rank + 1


    df = pd.DataFrame(table, columns=["Rank", "User", "P", "W", "L", "SR", "Change"], index=None)

    file_name = "mytable.png"
    if df.shape[0]:
        try:
            dfi.export(df.style.hide(axis='index'),"mytable.png")
        except Exception as e:
            print("Error exporting leaderboard: " + e)

    queue_record = queue_dao.get_queue(queue_id=queue_record.queue_id, guild_id=queue_record.guild_id)
    if len(queue_record.leaderboard_message_id) > 0:
        inter.delete_message(message_id=queue_record.leaderboard_message_id, channel_id=queue_record.leaderboard_channel_id)
    inter.send_file(file_name=file_name, channel_id=queue_record.leaderboard_channel_id)





