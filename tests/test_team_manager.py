"""Tests for TeamManager roster management and matchmaking."""

import pytest
from dao.TeamDao import TeamRecord, STATUS_IDLE, STATUS_QUEUED, STATUS_IN_MATCH
import core.TeamManager as TeamManager


def _team(team_id="t1", name="Alpha", captain="cap1", players=None, status=STATUS_IDLE,
          elo=25.0, sigma=8.33, team_sr=0.0, tmw=0, tml=0):
    return TeamRecord(
        guild_id="guild_123", team_id=team_id, team_name=name, captain_id=captain,
        players=players if players is not None else [captain],
        status=status, elo=elo, sigma=sigma, team_sr=team_sr, tmw=tmw, tml=tml,
    )


@pytest.fixture
def team_dao(mocker):
    mock = mocker.patch.object(TeamManager, "team_dao")
    mock.put_team = lambda t: None
    mock.delete_team = lambda g, tid: None
    mock.new_team = lambda guild_id, team_name, captain_id: _team(
        team_id="newid", name=team_name, captain=captain_id, players=[captain_id]
    )
    return mock


def _is_error(embed):
    return embed.color == TeamManager.ERROR_COLOR


# --- create_team -----------------------------------------------------------

class TestCreateTeam:
    def test_create_success(self, team_dao):
        team_dao.get_team_by_player.return_value = None
        embed = TeamManager.create_team("guild_123", "cap1", "Alpha")
        assert not _is_error(embed)
        assert "Alpha" in embed.title

    def test_create_rejected_if_already_on_team(self, team_dao):
        team_dao.get_team_by_player.return_value = _team()
        embed = TeamManager.create_team("guild_123", "cap1", "Beta")
        assert _is_error(embed)

    def test_create_rejects_blank_name(self, team_dao):
        team_dao.get_team_by_player.return_value = None
        embed = TeamManager.create_team("guild_123", "cap1", "   ")
        assert _is_error(embed)


# --- add_to_team -----------------------------------------------------------

class TestAddToTeam:
    def test_captain_adds_player(self, team_dao):
        def by_player(guild, pid):
            return _team() if pid == "cap1" else None
        team_dao.get_team_by_player.side_effect = by_player
        embed = TeamManager.add_to_team("guild_123", "cap1", "newp")
        assert not _is_error(embed)

    def test_non_captain_rejected(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(captain="cap1", players=["cap1", "p2"])
        embed = TeamManager.add_to_team("guild_123", "p2", "newp")
        assert _is_error(embed)

    def test_full_team_rejected(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2", "p3", "p4"])
        embed = TeamManager.add_to_team("guild_123", "cap1", "newp")
        assert _is_error(embed)

    def test_target_already_on_another_team(self, team_dao):
        def by_player(guild, pid):
            if pid == "cap1":
                return _team(team_id="t1", players=["cap1"])
            if pid == "newp":
                return _team(team_id="t2", name="Other", players=["newp"])
            return None
        team_dao.get_team_by_player.side_effect = by_player
        embed = TeamManager.add_to_team("guild_123", "cap1", "newp")
        assert _is_error(embed)

    def test_cannot_add_while_queued(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(status=STATUS_QUEUED)
        embed = TeamManager.add_to_team("guild_123", "cap1", "newp")
        assert _is_error(embed)


# --- kick_from_team --------------------------------------------------------

class TestKick:
    def test_captain_kicks(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2"])
        embed = TeamManager.kick_from_team("guild_123", "cap1", "p2")
        assert not _is_error(embed)

    def test_non_captain_cannot_kick(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2", "p3"])
        embed = TeamManager.kick_from_team("guild_123", "p2", "p3")
        assert _is_error(embed)

    def test_cannot_kick_self(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2"])
        embed = TeamManager.kick_from_team("guild_123", "cap1", "cap1")
        assert _is_error(embed)

    def test_kick_player_not_on_team(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2"])
        embed = TeamManager.kick_from_team("guild_123", "cap1", "ghost")
        assert _is_error(embed)


# --- leave_team ------------------------------------------------------------

class TestLeave:
    def test_member_leaves(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2"])
        embed = TeamManager.leave_team("guild_123", "p2")
        assert not _is_error(embed)

    def test_last_player_disbands(self, team_dao):
        deleted = {}
        team_dao.get_team_by_player.return_value = _team(players=["cap1"])
        team_dao.delete_team = lambda g, tid: deleted.update({"id": tid})
        embed = TeamManager.leave_team("guild_123", "cap1")
        assert "disbanded" in embed.title.lower()
        assert deleted.get("id") == "t1"

    def test_captain_leaving_reassigns_captaincy(self, team_dao):
        saved = {}
        team = _team(captain="cap1", players=["cap1", "p2", "p3"])
        team_dao.get_team_by_player.return_value = team
        team_dao.put_team = lambda t: saved.update({"captain": t.captain_id, "players": list(t.players)})
        TeamManager.leave_team("guild_123", "cap1")
        assert saved["captain"] == "p2"
        assert "cap1" not in saved["players"]

    def test_cannot_leave_during_match(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(status=STATUS_IN_MATCH, players=["cap1", "p2"])
        embed = TeamManager.leave_team("guild_123", "p2")
        assert _is_error(embed)


# --- queue_team ------------------------------------------------------------

class TestQueueTeam:
    def test_captain_queues_full_team(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2", "p3", "p4"])
        team_dao.get_queued_teams.return_value = [_team()]
        embed = TeamManager.queue_team("guild_123", "cap1")
        assert not _is_error(embed)

    def test_non_captain_cannot_queue(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(captain="cap1", players=["cap1", "p2", "p3", "p4"])
        embed = TeamManager.queue_team("guild_123", "p2")
        assert _is_error(embed)

    def test_incomplete_team_cannot_queue(self, team_dao):
        team_dao.get_team_by_player.return_value = _team(players=["cap1", "p2"])
        embed = TeamManager.queue_team("guild_123", "cap1")
        assert _is_error(embed)


# --- matchmaking -----------------------------------------------------------

class TestFairestPair:
    def test_picks_closest_rated_pair(self):
        # Ratings via elo - 2*sigma; vary elo to separate them.
        a = _team(team_id="a", elo=30.0, sigma=1.0)  # rating 28
        b = _team(team_id="b", elo=31.0, sigma=1.0)  # rating 29  (closest to a)
        c = _team(team_id="c", elo=50.0, sigma=1.0)  # rating 48  (far)
        x, y = TeamManager._pick_fairest_pair([a, b, c])
        chosen = {x.team_id, y.team_id}
        assert chosen == {"a", "b"}
