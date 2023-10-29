from discord_lambda import Embedding


def create_queue() -> Embedding:
    return Embedding("Underworld 8s", "Queue size: 0", color=0x880808)