from discord_lambda import Interaction, Embedding, CommandArg, CommandRegistry
import time


def ping_command(inter: Interaction, input: str) -> None:
    inter.send_response(content="Pong!")


def setup(registry: CommandRegistry) -> None:
    registry.register_cmd(func=ping_command, name="ping", desc="Pings the bot")