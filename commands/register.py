from core import QueueManager
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg
from venmoapi import VenmoApiAccessor

venmo = VenmoApiAccessor()
def register(inter: Interaction, venmo_user: str) -> None:
  payment_id = venmo.register_user(inter.user_id, inter.guild_id, venmo_user)
  embed = Embedding("Kali 8s Bot", f"Sent 8s registration fee for user {inter.username} with venmo: {venmo_user} and payment id: {payment_id} :smiley:.\n Please accept Venmo request to complete registration", color=0x00FF00)
  inter.send_response(embeds=[embed], ephemeral=False)

def setup(registry: CommandRegistry):
  registry.register_cmd(func=register, name="register", desc="Register for money 8s", options=[CommandArg("venmo_user", "Venmo User Name", CommandArg.Types.STRING)])



