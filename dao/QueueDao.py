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
  def __init__(self, guild_id: str, queue_id: str, team_1: list, team_2: list, queue: list, version: int, last_updated: float, message_id: str = None, channel_id: str = None):
    self.guild_id = guild_id
    self.queue_id = queue_id
    self.team_1 = team_1
    self.team_2 = team_2
    self.queue = queue
    self.version = int(version)
    self.message_id = message_id
    self.channel_id = channel_id
    self.last_updated = last_updated

  def clear_queue(self):
    self.team_1 = list()
    self.team_2 = list()
    self.queue = list()
    self.message_id = None
    self.channel_id = None

  def update_last_updated(self):
    self.last_updated = datetime.utcnow() + timedelta(minutes=1)

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
    queue_record.update_last_updated()

    current_version = queue_record.version
    queue_record.version = queue_record.version + 1
    json_ = json.dumps(queue_record.__dict__)
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


    return QueueRecord(guild_id=response["guild_id"], queue_id=response["queue_id"], last_updated=response["last_updated"], team_1=team_1, team_2=team_2, queue=queue, version=response["version"], message_id=response["message_id"], channel_id=response["channel_id"])
