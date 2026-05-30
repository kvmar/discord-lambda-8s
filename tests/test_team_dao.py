"""Tests for TeamRecord rating math (the team is the ranked entity)."""

from dao.TeamDao import TeamRecord, RANK_SR_RANGES


def _team(team_sr=200, team_rank=2, tmw=10, tml=5, elo=25.0, sigma=8.33):
    return TeamRecord(
        guild_id="guild_123",
        team_id="team_abc",
        team_name="Destroyers",
        captain_id="cap1",
        players=["cap1", "p2", "p3", "p4"],
        elo=elo,
        sigma=sigma,
        team_sr=team_sr,
        team_rank=team_rank,
        tmw=tmw,
        tml=tml,
    )


class TestTeamRpGain:
    def test_even_match_gain(self):
        assert _team().calculate_rp_gain(expected=0.5) == 10

    def test_underdog_win_gain(self):
        assert _team().calculate_rp_gain(expected=0.2) == 16

    def test_favourite_win_gain(self):
        assert _team().calculate_rp_gain(expected=0.8) == 4

    def test_minimum_gain_is_1(self):
        assert _team().calculate_rp_gain(expected=0.99) >= 1


class TestTeamRpLoss:
    def test_even_match_loss(self):
        assert _team().calculate_rp_loss(expected=0.5) == -10

    def test_favourite_loss(self):
        assert _team().calculate_rp_loss(expected=0.8) == -16

    def test_maximum_loss_is_neg_1(self):
        assert _team().calculate_rp_loss(expected=0.01) <= -1


class TestTeamApplyRpChange:
    def test_win_increases_sr(self):
        t = _team(team_sr=200)
        t.apply_rp_change(loss=0, expected=0.5)
        assert t.team_sr > 200

    def test_loss_decreases_sr(self):
        t = _team(team_sr=200)
        t.apply_rp_change(loss=1, expected=0.5)
        assert t.team_sr < 200

    def test_sr_floor_is_zero(self):
        t = _team(team_sr=3, team_rank=0)
        t.apply_rp_change(loss=1, expected=0.5)
        assert t.team_sr >= 0

    def test_delta_positive_on_win(self):
        t = _team(team_sr=200)
        t.apply_rp_change(loss=0, expected=0.5)
        assert t.team_delta.startswith("+")

    def test_delta_negative_on_loss(self):
        t = _team(team_sr=200)
        t.apply_rp_change(loss=1, expected=0.5)
        assert t.team_delta.startswith("-")

    def test_placement_fires_on_1st_game(self):
        # 1 game recorded before apply_rp_change is called (trueskill increments tmw first)
        t = _team(team_sr=50, team_rank=0, tmw=1, tml=0)
        t.apply_rp_change(loss=0, expected=0.5)
        assert t.team_sr == RANK_SR_RANGES[t.team_rank][0] + 50
        assert t.team_rank <= 3


class TestTeamHelpers:
    def test_is_full(self):
        assert _team().is_full() is True
        t = TeamRecord("g", "id", "n", "cap", players=["cap"])
        assert t.is_full() is False

    def test_is_ranked_threshold(self):
        assert _team(tmw=1, tml=0).is_ranked() is True   # 1 game
        assert _team(tmw=0, tml=0).is_ranked() is False  # 0 games

    def test_recruit_emoji_before_placement(self):
        t = _team(tmw=0, tml=0)
        assert "recruit" in t.get_rank_emoji()
