import os

import boto3

table_name = "QueueTable"

class QueueRecord:
  def __init__(self, guild_id: str, queue_id: str, team_1: set, team_2: set, queue: set):
    self.guild_id = guild_id
    self.queue_id = queue_id
    self.team_1 = team_1
    self.team_2 = team_2
    self.queue = queue

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
