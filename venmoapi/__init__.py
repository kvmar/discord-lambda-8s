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

    def deposit(self, player_id: str):
        pass

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





