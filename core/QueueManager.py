import json

from dao import set_default
from dao.QueueDao import QueueDao
from discord_lambda import Embedding
from discord_lambda import Components


join_queue_custom_id = "join_queue"
leave_queue_custom_id = "leave_queue"
start_queue_custom_id = "start_queue"

queue_dao = QueueDao()

def create_queue_resources(guild_id: str) -> (Embedding, Components):
    embed = Embedding("Underworld 8s", "Queue size: 0", color=0x880808)
    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)

    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {json.dumps(response.__dict__, default=set_default) } for guild_id: {guild_id}')

    return (embed, component)