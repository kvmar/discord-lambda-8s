from dao.PlayerBankDao import PlayerBankRecord, PlayerBankDao
from dao.PlayerDao import PlayerDao
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg
from venmoapi import VenmoApiAccessor

venmo = VenmoApiAccessor()
player_bank_dao = PlayerBankDao()
player_dao = PlayerDao()
def register(inter: Interaction, venmo_user: str) -> None:
  player_record = player_dao.get_player(player_id=inter.user_id, guild_id=inter.guild_id)
  if player_record is None:
    embed = Embedding("Kali 8s Bot", f"{inter.username} you must play 1 free 8s match before playing for money :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  player_bank_record = player_bank_dao.get_player_bank(inter.user_id)

  if player_bank_record is not None:
    if not player_bank_record.registration_complete:
      if venmo.is_payment_done(player_bank_record.registration_id):
        player_bank_record.registration_complete = True
        player_bank_dao.put_player_bank(player_record=player_bank_record)
        player_bank_record = player_bank_dao.get_player_bank(inter.user_id)

    if player_bank_record.registration_complete:
      embed = Embedding("Kali 8s Bot", f"Registration complete for user {inter.username} with venmo: {player_bank_record.venmo_user} :smiley:", color=0x00FF00)
      inter.send_response(embeds=[embed], ephemeral=False)
      return
    embed = Embedding("Kali 8s Bot", f"Registration still pending for user {inter.username} with venmo: {player_bank_record.venmo_user} :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  payment_id = venmo.register_user(inter.user_id, inter.guild_id, venmo_user)


  player_record = player_dao.get_player(player_id=inter.user_id, guild_id=inter.guild_id)
  embed = Embedding("Kali 8s Bot", f"Sent $1 Money 8s registration fee for user {player_record.player_name} with venmo: {venmo_user} :smiley:.\n "
                                   f"Please accept Venmo request to complete registration then type /register again", color=0x00FF00)
  player_bank_record = PlayerBankRecord(player_id=inter.user_id, registration_id=payment_id, venmo_user=venmo_user)
  player_bank_dao.put_player_bank(player_bank_record)
  inter.send_response(embeds=[embed], ephemeral=False)

def setup(registry: CommandRegistry):
  registry.register_cmd(func=register, name="register", desc="Register for money 8s", options=[CommandArg("venmo_user", "Venmo User Name", CommandArg.Types.STRING)])



