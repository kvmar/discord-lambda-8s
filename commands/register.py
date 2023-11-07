from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg

def register(inter: Interaction, venmo_user: str) -> None:
  embed = Embedding("Kali 8s Bot", f"Registered Money 8S user {inter.username} with venmo: {venmo_user} :smiley:", color=0x00FF00)
  inter.send_response(embeds=[embed], ephemeral=False)


def setup(registry: CommandRegistry):
  registry.register_cmd(func=register, name="register", desc="Register for money 8s", options=[CommandArg("venmo_user", "Venmo User Name", CommandArg.Types.STRING)])



