""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 6.1.0
"""
import os

import requests

from dao.PlayerBankDao import PlayerBankDao
from dao.PlayerDao import PlayerDao
from discord_lambda import Embedding

player_dao = PlayerDao()
player_bank_dao = PlayerBankDao()

base_api = "https://api.venmo.com/v1"

class VenmoApiAccessor:
    def __init__(self) -> None:
        self.env = os.environ.get('BOT_ENV')

    def register_user(self, player_id: str, guild_id: str, venmo_user: str):
        player_record = player_dao.get_player(player_id=player_id, guild_id=guild_id)
        payment_id = self.request_payment(venmo_user, f"Registration for user {player_record.player_name} to Kali 8s")
        print(payment_id)
        return payment_id
    def deposit(self, player_id: str, venmo_user: str, guild_id: str):
        player_record = player_dao.get_player(player_id=player_id, guild_id=guild_id)
        payment_id = self.request_payment(venmo_user, f"Deposit for user {player_record.player_name} to Kali 8s")
        print(payment_id)
        return payment_id

    def post_match(self, win_team, lose_team, interaction):
        complete_teams = win_team + lose_team
        for user in complete_teams:
            player_bank_record = player_bank_dao.get_player_bank(player_id=user)
            if player_bank_record.credits < 1:
                raise Exception(f"User has balance less than 1 {player_bank_record}")

        for user in win_team:
            player_bank_record = player_bank_dao.get_player_bank(player_id=user)
            player_bank_record.credits = player_bank_record.credits + 1
            player_bank_record.earnings = player_bank_record.credits + 1
            player_bank_dao.put_player_bank(player_bank_record)

        for user in lose_team:
            player_bank_record = player_bank_dao.get_player_bank(player_id=user)
            player_bank_record.credits = player_bank_record.credits - 1
            player_bank_record.earnings = player_bank_record.credits - 1
            player_bank_dao.put_player_bank(player_bank_record)

    def withdraw(self, player_id: str):
        pass

    def request_payment(self, venmo_user: str, description: str):
        try:
            headers = {
                "Authorization": f"Bearer {os.environ.get('VENMO_TOKEN')}",
                "User-Agent": "Venmo/7.44.0 (iPhone; iOS 13.0; Scale/2.0",
                "Content-Type": "application/json"
            }

            json = {
                "note": description,
                "amount": -1,
                "username": venmo_user,
                "audience": "private"
            }

            response = requests.post(f'{base_api}/payments', json=json, headers=headers)
            print(f'Got SendResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON SendResponse: {response.json}')
            return response.json()["data"]["payment"]["id"]
        except Exception as e:
            raise Exception(f"Unable to send message: {e}")

    def is_payment_done(self, payment_id: str):
        try:
            headers = {
                "Authorization": f"Bearer {os.environ.get('VENMO_TOKEN')}",
                "User-Agent": "Venmo/7.44.0 (iPhone; iOS 13.0; Scale/2.0",
                "Content-Type": "application/json"
            }

            response = requests.get(f'{base_api}/payments/{payment_id}', headers=headers)
            print(f'Got SendResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON SendResponse: {response.json}')
            status = response.json()["data"]["status"]

            if status == "settled":
                return True
            return False
        except Exception as e:
            raise Exception(f"Unable to send message: {e}")





