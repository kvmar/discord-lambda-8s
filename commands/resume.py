from core import QueueManager
from discord_lambda import CommandRegistry, Interaction, CommandArg
from dao.QueueDao import QueueDao

queue_dao = QueueDao()


def resume(inter: Interaction, queue_name: str = "1") -> None:
    """Re-post the queue embed from current DynamoDB state"""
    record = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_name)
    (embeds, components) = QueueManager.update_queue_embed(record)
    resp = inter.send_response(components=components, embeds=embeds, ephemeral=False)
    QueueManager.update_message_id(inter.guild_id, resp[0], resp[1], queue_id=queue_name)


def setup(registry: CommandRegistry):
    registry.register_cmd(
        func=resume,
        name="resume",
        desc="Re-posts the queue embed from current state (use if queue message breaks)",
        options=[CommandArg("queue_name", "Queue name", CommandArg.Types.STRING)]
    )
