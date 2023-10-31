from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction

queue_dao = QueueDao()
player_data = PlayerDao()

def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")
    player_data.get_player_by_guild_id(queue_record.guild_id)

