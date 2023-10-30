import json

from dao import set_default
from dao.QueueDao import QueueDao, QueueRecord
from discord_lambda import Embedding, Interaction
from discord_lambda import Components


join_queue_custom_id = "join_queue"
leave_queue_custom_id = "leave_queue"
start_queue_custom_id = "start_queue"

queue_dao = QueueDao()

def create_queue_resources(guild_id: str) -> (Embedding, Components):
    embed = Embedding("Underworld 8s", "Queue size: 0", color=0x880808)

    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {json.dumps(response.__dict__, default=set_default) } for guild_id: {guild_id}')

    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)


    response.clear_queue()
    queue_dao.put_queue(response)

    return embed, component


def add_player(inter: Interaction) -> (Embedding, Components):
    response = queue_dao.get_queue(inter.guild_id, "1")
    response.queue.add(inter.id)
    queue_dao.put_queue(response)

    (embed, component) = update_queue_embed(response)

    print(f'Queue record: {json.dumps(response.__dict__, default=set_default) } for guild_id: {inter.guild_id}')

    return embed, component


def update_queue_embed(record: QueueRecord) -> (Embedding, Components):
    queue_str = ""
    for user in record.queue:
        queue_str = queue_str + user + "\n"

    embed = Embedding(
        "Underworld 8s",
        f'Queue size: {len(record.queue)}\n\n{queue_str}',
        color=0x880808,
    )

    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)
    return embed, component

def update_message_id(guild_id, msg_id, channel_id):
    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {json.dumps(response.__dict__, default=set_default) } for guild_id: {guild_id}')

    response.message_id = msg_id
    response.channel_id = channel_id

    queue_dao.put_queue(response)