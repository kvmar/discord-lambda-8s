import json
import os

import boto3

from dao import set_default

table_name = "QueueTable"

class QueueRecord:
  def __init__(self, guild_id: str, queue_id: str, team_1: set, team_2: set, queue: set):
    self.guild_id = guild_id
    self.queue_id = queue_id
    self.team_1 = team_1
    self.team_2 = team_2
    self.queue = queue

  def clear_queue(self):
    self.team_1 = set()
    self.team_2 = set()
    self.queue = set()

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

    print(f'Queue Dao get_queue response: {response["Item"]}')
    return self.get_queue_record_attributes(response["Item"])

  def put_queue(self, queue_record: QueueRecord):
    response = self.table.put_item(Item=json.dumps(queue_record.__dict__, default=set_default))
    print(f'Queue Dao get_queue response: {response}')


  def get_queue_record_attributes(self, response):
    queue = set()
    for user in response['queue']:
      queue.add(user)

    team_1 = set()
    for user in response['team_1']:
      team_1.add(user)

    team_2 = set()
    for user in response['team_2']:
      team_2.add(user)


    return QueueRecord(response["guild_id"], response["queue_id"], team_1, team_2, queue)