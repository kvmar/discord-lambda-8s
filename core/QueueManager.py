import json
from datetime import datetime

from dao import set_default
from dao.PlayerDao import PlayerDao, PlayerRecord
from dao.QueueDao import QueueDao, QueueRecord
from discord_lambda import Embedding, Interaction
from discord_lambda import Components


join_queue_custom_id = "join_queue"
leave_queue_custom_id = "leave_queue"
start_queue_custom_id = "start_queue"

queue_dao = QueueDao()
player_dao = PlayerDao()

def create_queue_resources(guild_id: str) -> (Embedding, Components):
    embed = Embedding("Underworld 8s", "Queue size: 0", color=0x880808)

    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {response} for guild_id: {guild_id}')

    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)


    response.clear_queue()
    response.update_last_updated()

    queue_dao.put_queue(response)

    return embed, component


def add_player(inter: Interaction) -> (Embedding, Components):
    response = queue_dao.get_queue(inter.guild_id, "1")
    response.queue.append(inter.user_id)
    resp = queue_dao.put_queue(response)

    player_data = player_dao.get_player(guild_id=inter.guild_id, player_id=inter.user_id)

    if player_data is None:
        player_dao.put_player(PlayerRecord(guild_id=inter.guild_id, player_id=inter.user_id, player_name=inter.username))

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component

    return None

def remove_player(inter: Interaction) -> (Embedding, Components):
    response = queue_dao.get_queue(inter.guild_id, "1")

    if inter.user_id in response.queue:
        response.queue.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def update_queue_embed(record: QueueRecord) -> (Embedding, Components):
    queue_str = ""
    for user in record.queue:
        player_data = player_dao.get_player(record.guild_id, user)
        queue_str = queue_str + player_data.player_name + "\n"

    embed = Embedding(
        "Underworld 8s",
        f'Queue size: {len(record.queue)}\n\n{queue_str}',
        color=0x880808,
    )

    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)

    if len(record.queue) >= 8:
        component.add_button("Start queue", start_queue_custom_id, False, 3)
    else:
        component.add_button("Start queue", start_queue_custom_id, True, 3)

    return embed, component

def update_message_id(guild_id, msg_id, channel_id):
    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {response} for guild_id: {guild_id}')

    response.message_id = msg_id
    response.channel_id = channel_id

    queue_dao.put_queue(response)

def update_queue_view(record: QueueRecord, embeds: list[Embedding], components: list[Components], inter: Interaction):
    if int(datetime.utcnow().timestamp()) < record.last_updated:
        print(f"Queue message has expired: {record.last_updated}")
        record.update_last_updated()
        queue_dao.put_queue(record)
        resp = inter.edit_response(channel_id=record.channel_id, message_id=record.message_id, embeds=embeds, components=components)
        print(f'Queue message_id: {resp}')
        update_message_id(inter.guild_id, resp[0], resp[1])
    else:
        queue_dao.put_queue(record)
        inter.send_response(components=components, embeds=embeds, ephemeral=False)