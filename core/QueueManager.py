from discord_lambda import Embedding
from discord_lambda import Components


join_queue_custom_id = "join_queue"
leave_queue_custom_id = "join_queue"
start_queue_custom_id = "join_queue"

def create_queue_resources() -> (Embedding, Components):
    embed = Embedding("Underworld 8s", "Queue size: 0", color=0x880808)
    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)
    return (embed, component)