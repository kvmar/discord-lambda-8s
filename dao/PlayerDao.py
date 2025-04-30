import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dao import DecimalEncoder

table_name = "PlayerTable"

if os.environ.get('BOT_ENV') == "PROD":
  table_name = "PlayerTableProd"

class PlayerRecord:
  def __init__(self, guild_id: str, player_id: str, player_name: str, mw: int = 0, ml: int = 0, elo: float = 25.0, sigma: float = 8.33, delta: str = "+0.0", streak: int = 0, version: int = 0):
    self.guild_id = guild_id
    self.player_id = player_id
    self.player_name = player_name
    self.mw = mw
    self.ml = ml
    self.elo = elo
    self.sigma = sigma
    self.delta = delta
    self.streak = int(streak)
    self.version = version


  def get_streak(self):
    print("Streak for player_name: " + self.player_name + " , streak: " + str(self.streak))
    if self.streak == 2:
      return ":fire:"
    elif self.streak == 3:
      return "<a:blue_flame:1299111622807130132>"
    elif self.streak >= 4:
      return "<a:2788demonshit:1299111278572470423>"
    elif self.streak == -2:
      return ":monkey:"
    elif self.streak == -3:
      return "<:shitter:1299107333095297116>"
    elif self.streak <= -4:
      return "<a:spin_poop:1299111996964470805>"

    return ""

  def get_rating(self):
      return float(self.elo - (2 * self.sigma))

  def get_rank(self): 
      rating = self.get_rating() * 100
      if rating <= 500: 
        return ":Bronze:" + " "
      elif rating <= 1000: 
        return ":Silver:" + " "
      elif rating <= 1200:
        return ":monkey:" + " "
      elif rating <= 1400:
        return ":Diamond:" + " "
      elif rating <= 1600:
        return ":GrandMaster:" + " "
      elif rating <= 1800:
        return ":Celestial:" + " "
      elif rating <= 2000:
        return ":Eternity:" + " "
      else: 
        return ":OneAboveAll:" + " "


class PlayerDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def get_player(self, guild_id: str, player_id: str):
    response = self.table.get_item(
      Key={
        'player_id': player_id,
        'guild_id': guild_id,
      }
    )

    print(f'Player Dao get_player response: {response}')
    if 'Item' not in response:
      return None

    return self.get_player_record_attributes(response["Item"])

  def put_player(self, player_record: PlayerRecord):
    current_version = int(player_record.version)
    player_record.version = int(player_record.version) + 1
    json_ = json.dumps(player_record.__dict__, cls=DecimalEncoder)
    print(f'Putting following player_record: {json_}')
    player_dict = json.loads(json_, parse_float=Decimal)

    response = None
    try:
      if current_version != 0:
        response = self.table.put_item(Item=player_dict, ConditionExpression=Attr("version").eq(current_version))
      else:
        response = self.table.put_item(Item=player_dict)
    except ClientError as err:
      if err.response["Error"]["Code"] == 'ConditionalCheckFailedException':
        # Somebody changed the item in the db while we were changing it!
        print("Player updated since read, retry!")
        return response
      else:
        raise err

    print(f'PlayerDao put_player response: {response}')
    return response

  def get_players_by_guild_id(self, guild_id: str) -> list[PlayerRecord]:
      response = self.table.query(
        IndexName='guild_id-index',
        KeyConditionExpression=Key('guild_id').eq(guild_id)
      )

      print(f'Player Dao get_players_by_guild_id response: {response}')
      player_list = list()
      for player in response['Items']:
        player_list.append(self.get_player_record_attributes(player))
      return player_list

  def get_player_record_attributes(self, response):
      return PlayerRecord(player_id=response["player_id"], player_name=response['player_name'], guild_id=response["guild_id"], mw=response["mw"], ml=response["ml"], elo=response["elo"], sigma=response["sigma"], delta=response["delta"], streak=response["streak"], version=response["version"])
