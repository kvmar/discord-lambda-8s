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


RANK_ELO_RANGES = {
  0: (-9999, 499),
  1: (500, 999),
  2: (1000, 1199),
  3: (1200, 1399),
  4: (1400, 1599),
  5: (1600, 1799),
  6: (1800, 1999),
  7: (2000, 9000),
}

RANK_SR_RANGES = {
  0: (0, 99),
  1: (100, 199),
  2: (200, 299),
  3: (300, 399),
  4: (400, 499),
  5: (500, 599),
  6: (600, 699),
  7: (700, 9000),
}


class PlayerRecord:
  def __init__(self, guild_id: str, player_id: str, player_name: str, mw: int = 0, ml: int = 0, sr: float = 0.0, rank: int = 0, elo: float = 25.0, sigma: float = 8.33, delta: str = "+0.0", streak: int = 0, version: int = 0):
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

  def get_relative_skill(self):
      print("\n--- Get Relative Skill Debug ---")
      min_sr, max_sr = RANK_SR_RANGES[self.rank]
      print(f"SR Range for rank {self.rank}: {min_sr} to {max_sr}")
      print(f"Current SR: {self.sr}")

      rel_skill = (float(self.sr) - min_sr) / (max_sr - min_sr)
      print(f"Relative skill calculation: ({self.sr} - {min_sr}) / ({max_sr} - {min_sr}) = {rel_skill}")
      return max(0.0, min(rel_skill, 1.5))

  def get_tier_gap_modifier(self):
      print("\n--- Tier Gap Modifier Debug ---")
      tier_gap = self.calculate_proj_rank() - self.rank
      base = 1.0

      if tier_gap > 0:
          # If projected rank is higher, gain more and lose less
          base += 0.2 * float(tier_gap)
      elif tier_gap < 0:
          # If projected rank is lower, gain less and lose more
          base -= 0.2 * abs(tier_gap)

      print(f"Tier gap: {tier_gap}, Modifier: {max(0.25, base)}")
      return max(0.25, base)

  def calculate_rp_gain(self, base_gain=10):
    print("\n=== SR Gain Calculation Debug ===")
    print(f"Starting SR: {self.sr}")
    print(f"Current Rank: {self.rank}")

    rel_skill = self.get_relative_skill()
    print(f"Relative Skill: {rel_skill}")

    bonus = 10 * rel_skill
    print(f"Bonus (10 * rel_skill): {bonus}")

    modifier = self.get_tier_gap_modifier()
    print(f"Tier Gap Modifier: {modifier}")

    gain = float((base_gain + bonus)) * float(modifier)
    print(f"Final Calculation:")
    print(f"({base_gain} + {bonus}) * {modifier} = {gain}")
    print(f"Rounded gain: {round(gain)}")
    return max(1, round(gain))

  def calculate_rp_loss(self, base_loss=-10):
      print("\n--- RP Loss Calculation ---")
      rel_skill = self.get_relative_skill()
      print(f"Relative skill: {rel_skill}")
      penalty = 10 * (1 - rel_skill)
      print(f"Penalty: {penalty}")
      modifier = self.get_tier_gap_modifier()
      print(f"Tier gap modifier: {modifier}")
      loss = float((base_loss + penalty)) * float(modifier)

      print(f"Calculated loss: {loss}")
      return min(-5, min(0, round(loss)))  # Ensures at least -5 loss

  def apply_rp_change(self, loss):
      print("\n=== Apply RP Change Debug ===")
      print(f"Loss flag: {loss}")
      print(f"Initial SR: {self.sr}")
      print(f"Initial Rank: {self.rank}")
      curr_rank = self.rank
      curr_sr = self.sr

      if loss == 0:
        sr_gain = self.calculate_rp_gain()
        new_sr = curr_sr + sr_gain

        new_rank = self.calculate_sr_rank(new_sr)
        if curr_rank != new_rank:
            self.rank = new_rank
        self.sr = new_sr
        self.delta = "+" + str(int(float(self.sr - curr_sr)))
      else:
        sr_loss = self.calculate_rp_loss()  # This should return a negative number
        new_sr = max(0, curr_sr + sr_loss)  # Prevent SR from going below 0
        self.sr = new_sr
        self.rank = self.calculate_sr_rank(new_sr)
        self.delta = str(int(float(new_sr - curr_sr)))

      if self.mw + self.ml == 10:
        placement_rank = max(self.rank, self.calculate_proj_rank())
        self.rank = min(3, placement_rank)
        self.sr = RANK_SR_RANGES[self.rank][0] + 50
        self.delta = str(int(float(self.sr - curr_sr)))

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
      sr = 0
      if response.get("sr") is not None:
        sr = float(response['sr'])

      rank = 0
      if response.get("rank") is not None:
        rank = int(response['rank'])
      return PlayerRecord(player_id=response["player_id"], player_name=response['player_name'], guild_id=response["guild_id"], mw=response["mw"], ml=response["ml"], sr=sr, rank=rank, elo=response["elo"], sigma=response["sigma"], delta=response["delta"], streak=response["streak"], version=response["version"])
