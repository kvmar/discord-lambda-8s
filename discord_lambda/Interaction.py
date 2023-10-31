import os
from typing import Tuple, Any

import requests
import time

class Embedding:
    def __init__(self, title: str = "", desc: str = "", url: str = "", color: int = "", fields: list[dict] = [], footer: dict = {}, components: list[dict] = []):
        self.title = title
        self.desc = desc
        self.url = url
        self.color = color
        self.fields = fields
        self.footer = footer


    def to_dict(self):
        return {
            "title": self.title if self.title else None,
            "description": self.desc if self.desc else None,
            "url": self.url if self.url else None,
            "color": self.color if self.color else None,
            "fields": self.fields if self.fields else None,
            "footer": self.footer if self.footer else None,
        }
    

    def set_title(self, title: str):
        self.title = title
    

    def set_description(self, desc: str):
        self.desc = desc


    def set_url(self, url: str):
        self.url = url
    

    def set_color(self, color: int):
        self.color = color
    

    def add_field(self, name: str, value: str, inline: bool):
        # NEVER use append() here 
        self.fields = self.fields + [{"name": name, "value": value, "inline": inline}]
    

    def set_footer(self, text: str, icon_url: str = None):
        self.footer = {"text": text, "icon_url": icon_url}


class Components:
    def __init__(self, components: list[dict] = []):
        self.components = components

    def to_dict(self):
        return {
            "type": 1,
            "components": self.components if self.components else None
        }

    def add_button(self, label: str, custom_id: str, disabled: bool, style: int = 1):
        self.components = self.components + [{"style": style, "label": label, "custom_id": custom_id, "disabled": disabled, "type": 2}]


class Interaction:
    PING_RESPONSE = { "type": 1 }

    def __init__(self, interaction: dict, app_id: str) -> None:
        self.type = interaction.get("type")
        self.token = interaction.get("token")
        self.id = interaction.get("id")
        self.user_id = interaction.get("member").get("user").get("id")
        self.username = interaction.get("member").get("user").get("global_name")
        self.data = interaction.get("data")
        self.custom_id = interaction.get("data").get("custom_id")
        self.guild_id = interaction.get("guild").get("id")
        self.app_id = app_id
        self.callback_url = f"https://discord.com/api/v10/interactions/{self.id}/{self.token}/callback"
        self.webhook_url = f"https://discord.com/api/v10/webhooks/{self.app_id}/{self.token}/messages/@original"
        self.timestamp = time.time()
    

    def __create_channel_message(self, content: str = None, embeds: list[Embedding] = None, ephemeral: bool = True, components: list[Components] = None) -> dict:
        print(f'Creating channel message with ephemeral flag set to: {ephemeral}')
        response = {
            "content": content,
            "components": [component.to_dict() for component in components] if components else None,
            "embeds": [embed.to_dict() for embed in embeds] if embeds else None,
            "flags": 1 << 6 if ephemeral else None
        }
        return response

    def defer(self, ephemeral: bool = True) -> None:
        try:
            requests.post(self.callback_url, json={"type": 5, "data": {"flags": 1 << 6 if ephemeral else None}}).raise_for_status()
        except Exception as e:
            raise Exception(f"Unable to defer response: {e}")

    def pong(self, ephemeral: bool = True) -> None:
        try:
            requests.post(self.callback_url, json={"type": 6, "data": {"flags": 1 << 6 if ephemeral else None}}).raise_for_status()
        except Exception as e:
            raise Exception(f"Unable to pong response: {e}")

    def send_response(self, content: str = None, embeds: list[Embedding] = None, ephemeral: bool = True, components: list[Components] = None) -> \
    tuple[Any, Any]:
        try:
            json = self.__create_channel_message(content, embeds, ephemeral, components)
            print(f'Send Response json: {json}')
            response = requests.patch(self.webhook_url, json=json)
            print(f'Got SendResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON SendResponse: {response.json}')
            return response.json()['id'], response.json()['channel_id']
        except Exception as e:
            raise Exception(f"Unable to send response: {e}")

    def edit_response(self, channel_id: str, message_id: str, content: str = None, embeds: list[Embedding] = None, ephemeral: bool = False, components: list[Components] = None) :
        try:
            headers = {
                'Authorization': f'Bot {os.environ.get("BOT_TOKEN")}'
            }
            response = requests.delete(f'https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}', headers=headers)
            print(f'Got DeleteResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON DeleteResponse: {response.json}')

            return self.send_message(channel_id=channel_id, embeds=embeds, components=components)
        except Exception as e:
            raise Exception(f"Unable to delete response: {e}")

    def send_message(self, channel_id: str, content: str = None, embeds: list[Embedding] = None, ephemeral: bool = False, components: list[Components] = None):
        try:
            json = self.__create_channel_message(content, embeds, ephemeral, components)
            headers = {
                'Authorization': f'Bot {os.environ.get("BOT_TOKEN")}'
            }
            response = requests.post(f'https://discord.com/api/v10/channels/{channel_id}/messages', json=json, headers=headers)
            print(f'Got SendResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON SendResponse: {response.json}')
            return response.json()['id'], response.json()['channel_id']
        except Exception as e:
            raise Exception(f"Unable to delete response: {e}")

    def move_member(self, channel_id: str, guild_id: str, user_id: str):
        try:
            headers = {
                'Authorization': f'Bot {os.environ.get("BOT_TOKEN")}'
            }
            json = {
                "channel_id": channel_id
            }
            response = requests.patch(f'https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}', json=json, headers=headers)
            print(f'Got SendResponse: {response.text}')
            response.raise_for_status()
            print(f'Convert to JSON SendResponse: {response.json}')
        except Exception as e:
            print(f"Unable to move user: {e}")

    def send_followup(self, content: str = None, embeds: list[Embedding] = None, ephemeral: bool = True) -> None:
        try:
            requests.post(self.webhook_url, json=self.__create_channel_message(content, embeds, ephemeral)).raise_for_status()
        except Exception as e:
            raise Exception(f"Unable to send followup: {e}")
