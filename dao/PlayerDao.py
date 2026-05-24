from __future__ import annotations

import json
import os
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dao import DecimalEncoder

table_name = "PlayerTable"

if os.environ.get('BOT_ENV') == "PROD":
  table_name = "PlayerTableProd"


RANK_ELO_RANGES = {
  0: (-9999, 399),    # Bronze: 0-399
  1: (400, 699),      # Silver: 400-699
  2: (700, 1099),     # Gold: 700-1099
  3: (1100, 1399),    # Diamond: 1100-1399
  4: (1400, 1699),    # Master: 1400-1699
  5: (1700, 1899),    # GM: 1700-1899
  6: (1900, 2099),    # Celestial: 1900-2099
  7: (2100, 9000),    # One Above All: 2100+ (much harder to reach)
}

RANK_SR_RANGES = {
  0: (0, 99),
  1: (100, 199),
  2: (200, 299),
  3: (300, 399),
  4: (400, 499),
  5: (500, 599),
  6: (600, 699),
  7: (700, 800),
}


class PlayerRecord:
  def __init__(self, guild_id: str, player_id: str, player_name: str, mw: int = 0, ml: int = 0, sr: float = 0.0, rank: int = 0, elo: float = 25.0, sigma: float = 8.33, delta: str = "+0.0", streak: int = 0, version: int = 0, last_played: int = 0):
    self.guild_id = guild_id
    self.player_id = player_id
    self.player_name = player_name
    self.mw = mw
    self.ml = ml
    self.sr = sr
    self.rank = rank
    self.elo = elo
    self.sigma = sigma
    self.delta = delta
    self.streak = int(streak)
    self.version = version
    self.last_played = int(last_played)


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
      rating = float(self.elo - (2 * self.sigma))
      print(f"ELO: {self.elo}, Sigma: {self.sigma}, Rating: {rating}")
      return rating

  def get_effective_sr(self, grace_days: int = 7, decay_rate: int = 2) -> float:
      if self.last_played == 0:
          return float(self.sr)
      days_inactive = (int(time.time()) - self.last_played) / 86400
      decay = max(0.0, (days_inactive - grace_days) * decay_rate)
      return max(0.0, float(self.sr) - decay)

  def calculate_proj_rank(self):
    hidden_mmr = (self.get_rating()) * 100
    print("Hidden_mmr: " + str(hidden_mmr))
    for rank, (min_sr, max_sr) in RANK_ELO_RANGES.items():
      if min_sr <= hidden_mmr <= max_sr:
        return rank
    return max(RANK_ELO_RANGES.keys())

  def calculate_sr_rank(self, calc_sr):
    for rank, (min_sr, max_sr) in RANK_SR_RANGES.items():
      if min_sr <= calc_sr <= max_sr:
        return rank
    return max(RANK_SR_RANGES.keys())

  def get_rank_emoji(self):
      if self.mw + self.ml <= 9:
          return "<:recruit:1367977165618024491>"
      if self.rank == 0:
        return "<:Bronze:1367281599250563216>" 
      elif self.rank == 1:
        return "<:Silver:1367281173340094505>"
      elif self.rank == 2:
        return "<:Gold:1367281171729354812>"
      elif self.rank == 3:
        return "<:Diamond:1367281170613801101>"
      elif self.rank == 4:
        return "<:GrandMaster:1367282959870328842>"
      elif self.rank == 5:
        return "<:Celestial:1367281169137275090>"
      elif self.rank == 6:
        return "<:Eternity:1367281167954477158>"
      else: 
        return "<:OneAboveAll:1367281598143266949>"

  def calculate_rp_gain(self, base=20, expected=0.5):
      # expected = probability your team wins (ELO formula)
      # underdog win (expected=0.2) → +16; even (0.5) → +10; favourite (0.8) → +4
      gain = max(1, round(base * (1 - expected)))
      print(f"[RP gain] base={base} expected={expected:.2f} gain=+{gain}")
      return gain

  def calculate_rp_loss(self, base=20, expected=0.5):
      # favourite loss (expected=0.8) → -16; even (0.5) → -10; underdog (0.2) → -4
      loss = min(-1, -round(base * expected))
      print(f"[RP loss] base={base} expected={expected:.2f} loss={loss}")
      return loss

  def apply_rp_change(self, loss, expected=0.5):
      print(f"\n=== Apply RP Change: {'WIN' if loss == 0 else 'LOSS'} expected={expected:.2f} ===")

      # Commit accumulated decay before applying win/loss
      effective_sr = self.get_effective_sr()
      self.sr = effective_sr

      curr_sr = self.sr

      if loss == 0:
        sr_gain = self.calculate_rp_gain(expected=expected)
        new_sr = curr_sr + sr_gain
        self.rank = self.calculate_sr_rank(new_sr)
        self.sr = new_sr
        self.delta = "+" + str(int(float(self.sr - curr_sr)))
      else:
        sr_loss = self.calculate_rp_loss(expected=expected)
        new_sr = max(0, curr_sr + sr_loss)
        self.sr = new_sr
        self.rank = self.calculate_sr_rank(new_sr)
        self.delta = str(int(float(new_sr - curr_sr)))

      if self.mw + self.ml == 10:
        placement_rank = max(self.rank, self.calculate_proj_rank())
        self.rank = min(3, placement_rank)
        self.sr = RANK_SR_RANGES[self.rank][0] + 50
        self.delta = str(int(float(self.sr - curr_sr)))

      self.last_played = int(time.time())

class PlayerDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def get_player(self, guild_id: str, player_id: str):
    if guild_id != "1123491132765110302":
      guild_id = "1123491132765110302"
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
    if player_record.guild_id != "1123491132765110302":
       player_record.guild_id = "1123491132765110302"
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
      if guild_id != "1123491132765110302":
        guild_id = "1123491132765110302"
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
      sr = 0
      if response.get("sr") is not None:
        sr = float(response['sr'])

      rank = 0
      if response.get("rank") is not None:
        rank = int(response['rank'])
      last_played = 0
      if response.get("last_played") is not None:
        last_played = int(response["last_played"])
      return PlayerRecord(player_id=response["player_id"], player_name=response['player_name'], guild_id=response["guild_id"], mw=response["mw"], ml=response["ml"], sr=sr, rank=rank, elo=response["elo"], sigma=response["sigma"], delta=response["delta"], streak=response["streak"], version=response["version"], last_played=last_played)
