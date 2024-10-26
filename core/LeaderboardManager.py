from dao.LeaderboardDao import LeaderboardDao
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction, Embedding
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
        user_data.append(str(user.player_name))
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

def post_leaderboard_pretty(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")
    player_list = player_dao.get_players_by_guild_id(queue_record.guild_id)

    sorted_player_list = sorted(player_list, key=lambda x: x.elo, reverse=True)

    rank_str = ""
    name = ""
    p = ""
    w = ""
    l = ""
    sr = ""

    rank = 1
    for user in sorted_player_list:
        user_data = list()
        print(f"Got player: {user.player_name} with elo {user.elo}")
        if int(user.mw) + int(user.ml) >= 10:
            rank_str = rank_str + "\n" + rank
            name = name + "\n" + str(user.player_name)
            p = p + "\n" + str((int(user.mw) + int(user.ml)))
            w = w + "\n" + str((int(user.mw)))
            l = l + "\n" + str((int(user.ml)))
            sr = sr + "\n" + str(int(float(user.elo) * 100))
            rank = rank + 1


    leaderboard_record = leaderboard_dao.get_leaderboard(queue_record.guild_id)
    if len(leaderboard_record.leaderboard_message_id) > 0:
        inter.delete_message(message_id=leaderboard_record.leaderboard_message_id, channel_id=leaderboard_record.leaderboard_channel_id)
    embed = Embedding(
            title="Leaderboard",
            color=0x237FEB,
        )
    embed.add_field(name="Rank:",
                    value=rank_str, inline=False)
    embed.add_field(name="Name:",
                    value=name, inline=False)
    embed.add_field(name="P:",
                    value=p, inline=False)
    embed.add_field(name="W:",
                    value=w, inline=False)
    embed.add_field(name="L:",
                    value=l, inline=False)
    embed.add_field(name="SR:",
                    value=sr, inline=False)
    resp = inter.send_message(embeds=[embed], channel_id=leaderboard_record.leaderboard_channel_id)

    # If conditional write thrown then delete message
    leaderboard_record.leaderboard_message_id = resp[0]
    leaderboard_resp = leaderboard_dao.put_leaderboard(leaderboard_record)
    if leaderboard_resp is None:
        inter.delete_message(message_id=leaderboard_record.leaderboard_message_id, channel_id=leaderboard_record.leaderboard_channel_id)







