from dao.PlayerBankDao import PlayerBankRecord, PlayerBankDao
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg
from venmoapi import VenmoApiAccessor

venmo = VenmoApiAccessor()
player_bank_dao = PlayerBankDao()
def register(inter: Interaction, venmo_user: str) -> None:
  player_bank_record = player_bank_dao.get_player_bank(inter.user_id)

  if player_bank_record is not None:
    embed = Embedding("Kali 8s Bot", f"Registration complete for user {inter.username} with venmo: {player_bank_record.venmo_user} :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  payment_id = venmo.register_user(inter.user_id, inter.guild_id, venmo_user)
  embed = Embedding("Kali 8s Bot", f"Sent 8s registration fee for user {inter.username} with venmo: {venmo_user} and payment id: {payment_id} :smiley:.\n "
                                   f"Please accept Venmo request to complete registration then type /register again", color=0x00FF00)
  player_bank_record = PlayerBankRecord(player_id=inter.user_id, registration_id=payment_id, venmo_user=venmo_user)
  player_bank_dao.put_player_bank(player_bank_record)
  inter.send_response(embeds=[embed], ephemeral=False)

def setup(registry: CommandRegistry):
  registry.register_cmd(func=register, name="register", desc="Register for money 8s", options=[CommandArg("venmo_user", "Venmo User Name", CommandArg.Types.STRING)])



