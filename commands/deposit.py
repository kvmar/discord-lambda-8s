from dao.PlayerBankDao import PlayerBankRecord, PlayerBankDao
from dao.PlayerDao import PlayerDao
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg
from venmoapi import VenmoApiAccessor

venmo = VenmoApiAccessor()
player_dao = PlayerDao()
player_bank_dao = PlayerBankDao()

def deposit(inter: Interaction) -> None:
  player_bank_record = player_bank_dao.get_player_bank(inter.user_id)
  if player_bank_record is None:
    embed = Embedding("Kali 8s Bot", f"Register to Money 8s before depositing to balance using /register :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  if not player_bank_record.registration_complete:
    embed = Embedding("Kali 8s Bot", f"Registration still pending for user {inter.username} with venmo: {player_bank_record.venmo_user}. Please accept Venmo request :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  if player_bank_record.credits > 10:
    embed = Embedding("Kali 8s Bot", f"{inter.username} you cannot have a credit balance greater than 10 :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  player_record = player_dao.get_player(player_id=inter.user_id, guild_id=inter.guild_id)

  if player_bank_record.curr_transaction_id is not None:
      if venmo.is_payment_done(player_bank_record.curr_transaction_id):
        player_bank_record.curr_transaction_id = None
        player_bank_record.credits = player_bank_record.credits + 1
        player_bank_dao.put_player_bank(player_record=player_bank_record)
      else:
          embed = Embedding("Kali 8s Bot", f"{player_record.player_name} please accept your previous deposit Venmo request before depositing again :smiley:", color=0x00FF00)
          inter.send_response(embeds=[embed], ephemeral=False)
          return

  payment_id = venmo.deposit(player_id=inter.user_id, guild_id=inter.guild_id, venmo_user=player_bank_record.venmo_user)
  player_bank_record.curr_transaction_id = payment_id
  player_bank_dao.put_player_bank(player_record=player_bank_record)
  embed = Embedding("Kali 8s Bot", f"{player_record.player_name} sent $1 deposit request. Please accept venmo to update balance. :smiley:", color=0x00FF00)
  inter.send_response(embeds=[embed], ephemeral=False)

def setup(registry: CommandRegistry):
  registry.register_cmd(func=deposit, name="deposit", desc="Deposit $1 to balance", options=[])



