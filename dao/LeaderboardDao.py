import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from dao import set_default

table_name = "GuildToLeaderboardMappingTable"

if os.environ.get('BOT_ENV') == "PROD":
  table_name = "GuildToLeaderboardMappingTableProd"

class LeaderboardRecord:
  def __init__(self, guild_id: str, leaderboard_channel_id: str, leaderboard_message_id: str, version: int):
    self.guild_id = guild_id
    self.leaderboard_channel_id = leaderboard_channel_id
    self.leaderboard_message_id = leaderboard_message_id
    self.version = version

class LeaderboardDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def get_leaderboard(self, guild_id: str):
    response = self.table.get_item(
      Key={
        'guild_id': guild_id,
      }
    )

    print(f'Leaderboard Dao get_leaderboard response: {response}')
    return self.get_leaderboard_record_attributes(response["Item"])

  def put_leaderboard(self, leaderboard_record: LeaderboardRecord):
    current_version = leaderboard_record.version
    leaderboard_record.version = leaderboard_record.version + 1
    json_ = json.dumps(leaderboard_record.__dict__, default=set_default)
    print(f'Putting following queue_record: {json_}')
    leaderboard_dict = json.loads(json_, parse_float=Decimal)

    response = None
    try:
      response = self.table.put_item(Item=leaderboard_dict, ConditionExpression=Attr("version").eq(current_version))
    except ClientError as err:
      if err.response["Error"]["Code"] == 'ConditionalCheckFailedException':
        # Somebody changed the item in the db while we were changing it!
        print("Leaderboard updated since read, retry!")
        return response
      else:
        raise err

    print(f'Leaderboard Dao put_leaderboard response: {response}')
    return response


  def get_leaderboard_record_attributes(self, response):
    return LeaderboardRecord(guild_id=response["guild_id"], leaderboard_channel_id=response["leaderboard_channel_id"], version=response["leaderboard_message_id"], version=response["version"])
