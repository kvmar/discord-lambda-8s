import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from dao import set_default

table_name = "QueueTable"

class QueueRecord:
  def __init__(self, guild_id: str, queue_id: str, team_1: list, team_2: list, queue: list, cancel_votes: list, team1_votes: list, team2_votes: list, maps: list, version: int, expiry: int, result_channel_id: str,
      team_1_channel_id: str, team_2_channel_id: str, leaderboard_channel_id: str, leaderboard_message_id: str,message_id: str = None, channel_id: str = None):
    self.guild_id = guild_id
    self.queue_id = queue_id
    self.team_1 = team_1
    self.team_2 = team_2
    self.cancel_votes = cancel_votes
    self.team1_votes = team1_votes
    self.team2_votes = team2_votes
    self.maps = maps
    self.queue = queue
    self.version = int(version)
    self.message_id = message_id
    self.channel_id = channel_id
    self.team_1_channel_id = team_1_channel_id
    self.team_2_channel_id = team_2_channel_id
    self.expiry = expiry
    self.result_channel_id = result_channel_id
    self.leaderboard_channel_id = leaderboard_channel_id
    self.leaderboard_message_id = leaderboard_message_id

  def clear_queue(self):
    self.team_1 = list()
    self.team_2 = list()
    self.queue = list()
    self.cancel_votes = list()
    self.team1_votes = list()
    self.team2_votes = list()
    self.maps = list()
    self.message_id = None
    self.channel_id = None
    self.update_expiry_date()

  def update_expiry_date(self):
    time = datetime.utcnow() + timedelta(minutes=10)
    self.expiry = int(time.timestamp())

class QueueDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def get_queue(self, guild_id: str, queue_id: str):
    response = self.table.get_item(
      Key={
        'guild_id': guild_id,
        'queue_id': queue_id,
      }
    )

    print(f'Queue Dao get_queue response: {response}')
    return self.get_queue_record_attributes(response["Item"])

  def put_queue(self, queue_record: QueueRecord):
    current_version = queue_record.version
    queue_record.version = queue_record.version + 1
    json_ = json.dumps(queue_record.__dict__, default=set_default)
    print(f'Putting following queue_record: {json_}')
    queue_dict = json.loads(json_, parse_float=Decimal)

    response = None
    try:
      response = self.table.put_item(Item=queue_dict, ConditionExpression=Attr("version").eq(current_version))
    except ClientError as err:
      if err.response["Error"]["Code"] == 'ConditionalCheckFailedException':
        # Somebody changed the item in the db while we were changing it!
        print("Queue updated since read, retry!")
        return response
      else:
        raise err

    print(f'Queue Dao put_queue response: {response}')
    return response


  def get_queue_record_attributes(self, response):
    queue = list()
    for user in response['queue']:
      queue.append(user)

    team_1 = list()
    for user in response['team_1']:
      team_1.append(user)

    team_2 = list()
    for user in response['team_2']:
      team_2.append(user)

    cancel_votes = list()
    for user in response['cancel_votes']:
      cancel_votes.append(user)

    team1_votes = list()
    for user in response['team1_votes']:
      team1_votes.append(user)

    team2_votes = list()
    for user in response['team2_votes']:
      team2_votes.append(user)

    maps = list()
    for map in response['maps']:
      maps.append(map)

    return QueueRecord(guild_id=response["guild_id"], queue_id=response["queue_id"], expiry=int(response["expiry"]),
                       team_1=team_1, team_2=team_2, queue=queue, cancel_votes=cancel_votes,
                       leaderboard_channel_id=response["leaderboard_channel_id"], leaderboard_message_id=response["leaderboard_message_id"],
                       result_channel_id=response["result_channel_id"],
                       team_1_channel_id=response["team_1_channel_id"], team_2_channel_id=response["team_2_channel_id"],
                       team1_votes=team1_votes, team2_votes=team2_votes, maps=maps,
                       version=response["version"], message_id=response["message_id"], channel_id=response["channel_id"])
