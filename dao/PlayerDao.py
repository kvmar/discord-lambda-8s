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
  def __init__(self, guild_id: str, player_id: str, player_name: str, mw: int = 0, ml: int = 0, elo: float = 25.0, sigma: float = 8.33, delta: str = "+0.0",  sr_delta: str = "+0.0", sr: float = 25.0, sr_sigma: float = 8.33, version: int = 0):
    self.guild_id = guild_id
    self.player_id = player_id
    self.player_name = player_name
    self.mw = mw
    self.ml = ml
    self.elo = elo
    self.sigma = sigma
    self.delta = delta
    self.sr = sr
    self.sr_sigma = sr_sigma
    self.sr_delta = sr_delta
    self.version = version

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
      sr = 25.0
      if response.get("sr") is not None:
          sr = response['sr']

      sr_sigma = 8.33
      if response.get("sr_sigma") is not None:
        sr_sigma = response['sr_sigma']

      sr_delta = "+0.0"
      if response.get("sr_delta") is not None:
        sr_delta = response['sr_delta']
      return PlayerRecord(sr_delta=sr_delta, sr=sr, sr_sigma=sr_sigma, player_id=response["player_id"], player_name=response['player_name'], guild_id=response["guild_id"], mw=response["mw"], ml=response["ml"], elo=response["elo"], sigma=response["sigma"], delta=response["delta"], version=response["version"])