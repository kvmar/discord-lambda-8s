from discord_lambda import Embedding

join_queue_custom_id = "join_queue"
leave_queue_custom_id = "join_queue"
start_queue_custom_id = "join_queue"

def create_queue() -> Embedding:
    embed = Embedding("Underworld 8s", "Queue size: 0", color=0x880808)
    embed.add_button("Join queue", join_queue_custom_id, False, 1)
    embed.add_button("Leave queue", leave_queue_custom_id, False, 4)
    embed.add_button("Start queue", start_queue_custom_id, True, 3)
    return embed