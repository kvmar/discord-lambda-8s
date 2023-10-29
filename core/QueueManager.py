from dao.QueueDao import QueueDao, QueueRecord
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
    queue_record = get_queue_record_attributes(response)

    queue = QueueRecord(queue_record[0], queue_record[1], queue_record[2], queue_record[3], queue_record[4])
    print(f'Queue record: {queue} for guild_id: {guild_id}')

    return (embed, component)


def get_queue_record_attributes(response):
    queue = set()
    for user in response['queue']:
        print(f'Found user: {user} in queue')
        queue.add(user)

    team_1 = set()
    for user in response['team_1']:
        print(f'Found user: {user} in team_1')
        team_1.add(user)

    team_2 = set()
    for user in response['team_2']:
        print(f'Found user: {user} in team_2')
        team_2.add(user)


    return (response["guild_id"], response["queue_id"], team_1, team_2, queue)