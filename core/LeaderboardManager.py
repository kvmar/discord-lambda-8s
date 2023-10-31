from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction

queue_dao = QueueDao()
player_data = PlayerDao()

def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")
    player_list = player_data.get_players_by_guild_id(queue_record.guild_id)

    sorted_player_list = sorted(player_list, key=lambda x: x.elo, reverse=True)

    for user in sorted_player_list:
        print(f"Got player: {user.player_name} with elo {user.elo}")

