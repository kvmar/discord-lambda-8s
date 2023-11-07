from dao.PlayerBankDao import PlayerBankRecord, PlayerBankDao
from dao.PlayerDao import PlayerDao
from discord_lambda import Embedding, CommandRegistry, Interaction, CommandArg
from venmoapi import VenmoApiAccessor

venmo = VenmoApiAccessor()
player_bank_dao = PlayerBankDao()
player_dao = PlayerDao()

def balance(inter: Interaction) -> None:
  player_bank_record = player_bank_dao.get_player_bank(inter.user_id)
  if player_bank_record is None:
    embed = Embedding("Kali 8s Bot", f"Register to Money 8s before checking balance using /register :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  if not player_bank_record.registration_complete:
    embed = Embedding("Kali 8s Bot", f"Registration still pending for user {inter.username} with venmo: {player_bank_record.venmo_user}. Please accept venmo request :smiley:", color=0x00FF00)
    inter.send_response(embeds=[embed], ephemeral=False)
    return

  player_record = player_dao.get_player(inter.user_id, inter.guild_id)

  deposit_on_hold = ""
  if player_bank_record.curr_transaction_id is not None:
    deposit_on_hold = " There is a $1 deposit still pending completion on Venmo"

  embed = Embedding("Kali 8s Bot", f"{player_record.player_name} has a balance of {player_bank_record.credits}.{deposit_on_hold} :smiley:", color=0x00FF00)
  inter.send_response(embeds=[embed], ephemeral=False)

def setup(registry: CommandRegistry):
  registry.register_cmd(func=balance, name="balance", desc="Get current credit balance", options=[])



