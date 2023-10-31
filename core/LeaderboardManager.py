from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction
from table2ascii import table2ascii as t2a, PresetStyle


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

    # In your command:
    output = t2a(
        header=["Rank", "User", "P", "W", "L", "SR", "Change"],
        body=table,
        style=PresetStyle.thin_compact
    )
    queue_record = queue_dao.get_queue(queue_id=queue_record.queue_id, guild_id=queue_record.guild_id)
    if len(queue_record.leaderboard_message_id) > 0:
        inter.delete_message(message_id=queue_record.leaderboard_message_id, channel_id=queue_record.leaderboard_channel_id)
    resp = inter.send_message(content=f"```\n{output}\n```", channel_id=queue_record.leaderboard_channel_id)
    queue_record.leaderboard_message_id = resp[0]
    queue_dao.put_queue(queue_record=queue_record)






