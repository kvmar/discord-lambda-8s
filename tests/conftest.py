"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from types import ModuleType

# Mock trueskill and more_itertools before any project imports
trueskill_mock = ModuleType('trueskill')
trueskill_mock.TrueSkill = MagicMock()
trueskill_mock.Rating = MagicMock()
sys.modules['trueskill'] = trueskill_mock

more_itertools_mock = ModuleType('more_itertools')
more_itertools_mock.set_partitions = MagicMock(return_value=[])
sys.modules['more_itertools'] = more_itertools_mock

table2ascii_mock = ModuleType('table2ascii')
table2ascii_mock.table2ascii = MagicMock()
table2ascii_mock.PresetStyle = MagicMock()
sys.modules['table2ascii'] = table2ascii_mock

# Create mock boto3 module structure
boto3_mock = ModuleType('boto3')
botocore_mock = ModuleType('botocore')
botocore_exceptions = ModuleType('botocore.exceptions')

# Add to sys.modules before any imports
sys.modules['boto3'] = boto3_mock
sys.modules['boto3.dynamodb'] = ModuleType('boto3.dynamodb')
sys.modules['boto3.dynamodb.conditions'] = ModuleType('boto3.dynamodb.conditions')
sys.modules['botocore'] = botocore_mock
sys.modules['botocore.exceptions'] = botocore_exceptions

# Add mock attributes
boto3_mock.Session = MagicMock()
boto3_mock.resource = MagicMock()
sys.modules['boto3.dynamodb.conditions'].Attr = MagicMock()
sys.modules['boto3.dynamodb.conditions'].Key = MagicMock()
botocore_exceptions.ClientError = Exception

from dao.QueueDao import QueueRecord
from discord_lambda import Interaction


@pytest.fixture
def mock_interaction():
    """Create a mock Interaction object for testing."""
    inter = MagicMock(spec=Interaction)
    inter.guild_id = "guild_123"
    inter.user_id = "user_456"
    inter.username = "TestPlayer"
    inter.custom_id = "join_pre_queue#main"
    inter.send_response = MagicMock()
    inter.send_message = MagicMock()
    inter.edit_response = MagicMock(return_value=["msg_id", "ch_id"])
    inter.edit_message = MagicMock(return_value=["msg_id", "ch_id"])
    return inter


@pytest.fixture
def queue_record_waiting():
    """Create a QueueRecord in Waiting state (no game in progress)."""
    return QueueRecord(
        guild_id="guild_123",
        queue_id="main",
        team_1=[],
        team_2=[],
        queue=["user1", "user2", "user3"],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=[],
        map_set=["Map1", "Map2", "Map3"],
        version=1,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        money_queue=False,
        pre_queue=[],
    )


@pytest.fixture
def queue_record_picking():
    """Create a QueueRecord in Picking state (captains assigned, teams being filled)."""
    return QueueRecord(
        guild_id="guild_123",
        queue_id="main",
        team_1=["cap1"],
        team_2=["cap2"],
        queue=["user3", "user4", "user5", "user6", "user7", "user8"],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=["Map1"],
        map_set=["Map1", "Map2", "Map3"],
        version=2,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        money_queue=False,
        pre_queue=[],
    )


@pytest.fixture
def queue_record_match_ready():
    """Create a QueueRecord in Match Ready state (game about to start)."""
    return QueueRecord(
        guild_id="guild_123",
        queue_id="main",
        team_1=["cap1", "user1", "user2", "user3"],
        team_2=["cap2", "user4", "user5", "user6"],
        queue=[],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=["Map1", "Map2", "Map3"],
        map_set=["Map1", "Map2", "Map3"],
        version=3,
        expiry=9999999999,
        result_channel_id="result_ch",
        team_1_channel_id="team1_ch",
        team_2_channel_id="team2_ch",
        money_queue=False,
        pre_queue=[],
    )


def _create_mock_player(player_id="user_456", player_name="TestPlayer"):
    """Helper to create a properly configured mock player."""
    player = MagicMock()
    player.player_id = player_id
    player.player_name = player_name
    player.sr = 2000
    player.get_rating = MagicMock(return_value=2000)
    player.get_rank_emoji = MagicMock(return_value="🥇")
    player.get_streak = MagicMock(return_value="")
    player.delta = "+50"
    return player


@pytest.fixture
def mock_player_dao(mocker):
    """Mock PlayerDao for testing."""
    mock = mocker.patch('core.QueueManager.player_dao')

    # Side effect to create players with correct IDs
    def get_player_side_effect(guild_id, player_id):
        return _create_mock_player(player_id=player_id, player_name=f"Player_{player_id}")

    mock.get_player = MagicMock(side_effect=get_player_side_effect)
    mock.put_player = MagicMock()
    return mock


@pytest.fixture
def mock_queue_dao(mocker):
    """Mock QueueDao for testing."""
    mock = mocker.patch('core.QueueManager.queue_dao')
    mock.put_queue = MagicMock(return_value=None)
    mock.get_queue = MagicMock(return_value=None)
    return mock
