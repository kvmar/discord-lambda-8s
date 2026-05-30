from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from dao import DecimalEncoder
from dao.PlayerDao import RANK_SR_RANGES, RANK_ELO_RANGES

table_name = "TeamTable"

if os.environ.get('BOT_ENV') == "PROD":
  table_name = "TeamTableProd"


MAX_TEAM_SIZE = 4

# Team lifecycle states
STATUS_IDLE = "idle"        # roster being built, not searching
STATUS_QUEUED = "queued"    # full roster, in the matchmaking pool
STATUS_IN_MATCH = "in_match"  # currently playing a match


class TeamRecord:
  """A premade 4v4 team. The team itself is the ranked entity — elo/sigma and
  team_sr live here, not on individual players, so a roster carries its own
  rating across matches."""

  def __init__(self, guild_id: str, team_id: str, team_name: str, captain_id: str,
      players: list = None, status: str = STATUS_IDLE,
      elo: float = 25.0, sigma: float = 8.33, team_sr: float = 0.0, team_rank: int = 0,
      team_delta: str = "+0", tmw: int = 0, tml: int = 0, version: int = 0):
    self.guild_id = guild_id
    self.team_id = team_id
    self.team_name = team_name
    self.captain_id = captain_id
    self.players = players if players is not None else list()
    self.status = status
    self.elo = elo
    self.sigma = sigma
    self.team_sr = team_sr
    self.team_rank = team_rank
    self.team_delta = team_delta
    self.tmw = int(tmw)
    self.tml = int(tml)
    self.version = int(version)

  def get_rating(self):
    rating = float(self.elo - (2 * self.sigma))
    print(f"[Team {self.team_name}] ELO: {self.elo}, Sigma: {self.sigma}, Rating: {rating}")
    return rating

  def is_full(self) -> bool:
    return len(self.players) >= MAX_TEAM_SIZE

  def is_ranked(self) -> bool:
    return (self.tmw + self.tml) >= 1

  def calculate_proj_rank(self):
    hidden_mmr = self.get_rating() * 100
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
    if self.tmw + self.tml == 0:
      return "<:recruit:1367977165618024491>"
    if self.team_rank == 0:
      return "<:Bronze:1367281599250563216>"
    elif self.team_rank == 1:
      return "<:Silver:1367281173340094505>"
    elif self.team_rank == 2:
      return "<:Gold:1367281171729354812>"
    elif self.team_rank == 3:
      return "<:Diamond:1367281170613801101>"
    elif self.team_rank == 4:
      return "<:GrandMaster:1367282959870328842>"
    elif self.team_rank == 5:
      return "<:Celestial:1367281169137275090>"
    elif self.team_rank == 6:
      return "<:Eternity:1367281167954477158>"
    else:
      return "<:OneAboveAll:1367281598143266949>"

  def calculate_rp_gain(self, base=20, expected=0.5):
    gain = max(1, round(base * (1 - expected)))
    print(f"[Team RP gain] base={base} expected={expected:.2f} gain=+{gain}")
    return gain

  def calculate_rp_loss(self, base=20, expected=0.5):
    loss = min(-1, -round(base * expected))
    print(f"[Team RP loss] base={base} expected={expected:.2f} loss={loss}")
    return loss

  def apply_rp_change(self, loss, expected=0.5):
    print(f"\n=== Team RP Change [{self.team_name}]: {'WIN' if loss == 0 else 'LOSS'} expected={expected:.2f} ===")
    curr_sr = float(self.team_sr)

    if loss == 0:
      sr_gain = self.calculate_rp_gain(expected=expected)
      new_sr = curr_sr + sr_gain
      self.team_rank = self.calculate_sr_rank(new_sr)
      self.team_sr = new_sr
      self.team_delta = "+" + str(int(float(self.team_sr - curr_sr)))
    else:
      sr_loss = self.calculate_rp_loss(expected=expected)
      new_sr = max(0, curr_sr + sr_loss)
      self.team_sr = new_sr
      self.team_rank = self.calculate_sr_rank(new_sr)
      self.team_delta = str(int(float(new_sr - curr_sr)))

    # Placement: after the 1st team game, seed rank from hidden MMR (capped at Diamond)
    if self.tmw + self.tml == 1:
      placement_rank = max(self.team_rank, self.calculate_proj_rank())
      self.team_rank = min(3, placement_rank)
      self.team_sr = RANK_SR_RANGES[self.team_rank][0] + 50
      self.team_delta = str(int(float(self.team_sr - curr_sr)))


class TeamDao:
  def __init__(self):
    session = boto3.Session(
      aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
      aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    self.table = dynamodb.Table(table_name)

  def new_team(self, guild_id: str, team_name: str, captain_id: str) -> TeamRecord:
    return TeamRecord(
      guild_id=guild_id,
      team_id=str(uuid.uuid4()),
      team_name=team_name,
      captain_id=captain_id,
      players=[captain_id],
      status=STATUS_IDLE,
    )

  def get_team(self, guild_id: str, team_id: str):
    response = self.table.get_item(
      Key={
        'team_id': team_id,
        'guild_id': guild_id,
      }
    )
    print(f'Team Dao get_team response: {response}')
    if 'Item' not in response:
      return None
    return self.get_team_record_attributes(response["Item"])

  def get_teams_by_guild_id(self, guild_id: str) -> list[TeamRecord]:
    response = self.table.query(
      IndexName='guild_id-index',
      KeyConditionExpression=Key('guild_id').eq(guild_id)
    )
    print(f'Team Dao get_teams_by_guild_id response: {response}')
    teams = list()
    for item in response['Items']:
      teams.append(self.get_team_record_attributes(item))
    return teams

  def get_team_by_player(self, guild_id: str, player_id: str):
    """Returns the team this player currently belongs to, or None."""
    for team in self.get_teams_by_guild_id(guild_id):
      if player_id in team.players:
        return team
    return None

  def get_queued_teams(self, guild_id: str) -> list[TeamRecord]:
    return [t for t in self.get_teams_by_guild_id(guild_id) if t.status == STATUS_QUEUED]

  def put_team(self, team_record: TeamRecord):
    current_version = int(team_record.version)
    team_record.version = int(team_record.version) + 1
    json_ = json.dumps(team_record.__dict__, cls=DecimalEncoder)
    print(f'Putting following team_record: {json_}')
    team_dict = json.loads(json_, parse_float=Decimal)

    response = None
    try:
      if current_version != 0:
        response = self.table.put_item(Item=team_dict, ConditionExpression=Attr("version").eq(current_version))
      else:
        response = self.table.put_item(Item=team_dict)
    except ClientError as err:
      if err.response["Error"]["Code"] == 'ConditionalCheckFailedException':
        print("Team updated since read, retry!")
        return response
      else:
        raise err

    print(f'Team Dao put_team response: {response}')
    return response

  def delete_team(self, guild_id: str, team_id: str):
    response = self.table.delete_item(
      Key={
        'team_id': team_id,
        'guild_id': guild_id,
      }
    )
    print(f'Team Dao delete_team response: {response}')
    return response

  def get_team_record_attributes(self, response):
    players = list()
    if response.get("players") is not None:
      for p in response["players"]:
        players.append(p)

    elo = 25.0
    if response.get("elo") is not None:
      elo = float(response["elo"])

    sigma = 8.33
    if response.get("sigma") is not None:
      sigma = float(response["sigma"])

    team_sr = 0.0
    if response.get("team_sr") is not None:
      team_sr = float(response["team_sr"])

    team_rank = 0
    if response.get("team_rank") is not None:
      team_rank = int(response["team_rank"])

    return TeamRecord(
      guild_id=response["guild_id"],
      team_id=response["team_id"],
      team_name=response["team_name"],
      captain_id=response["captain_id"],
      players=players,
      status=response.get("status", STATUS_IDLE),
      elo=elo,
      sigma=sigma,
      team_sr=team_sr,
      team_rank=team_rank,
      team_delta=response.get("team_delta", "+0"),
      tmw=int(response.get("tmw", 0)),
      tml=int(response.get("tml", 0)),
      version=response["version"],
    )
