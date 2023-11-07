import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dao import DecimalEncoder

table_name = "PlayerBankTable"

if os.environ.get('BOT_ENV') == "PROD":
  table_name = "PlayerBankTableProd"

class PlayerBankRecord:
  def __init__(self, player_id: str, venmo_user: str = None, registration_id: str = None, credits: int = 0, earnings: int = 0,
      curr_transaction_id: str = None, registration_complete: bool = False, version: int = 0):
    self.player_id = player_id
    self.venmo_user = venmo_user
    self.registration_id = registration_id
    self.registration_complete = registration_complete
    self.credits = credits
    self.curr_transaction_id = curr_transaction_id
    self.earnings = earnings
    self.version = version

class PlayerBankDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def get_player_bank(self, player_id: str):
    response = self.table.get_item(
      Key={
        'player_id': player_id,
      }
    )

    print(f'Player Bank Dao get_player_bank response: {response}')
    if 'Item' not in response:
      return None

    return self.get_player_bank_record_attributes(response["Item"])

  def put_player_bank(self, player_record: PlayerBankRecord):
    current_version = int(player_record.version)
    player_record.version = int(player_record.version) + 1
    json_ = json.dumps(player_record.__dict__, cls=DecimalEncoder)
    print(f'Putting following player_bank_record: {json_}')
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
        print("Player bank updated since read, retry!")
        return response
      else:
        raise err

    print(f'PlayerDao put_player response: {response}')
    return response

  def get_player_bank_record_attributes(self, response):
      return PlayerBankRecord(player_id=response["player_id"], registration_id=response['registration_id'], venmo_user=response['venmo_user'],
                              registration_complete=response['registration_complete'], credits=response["credits"], earnings=response["earnings"],
                              curr_transaction_id=response["curr_transaction_id"], version=response["version"])