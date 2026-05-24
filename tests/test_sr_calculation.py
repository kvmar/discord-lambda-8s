"""Tests for SR gain/loss/rank and decay calculations."""

import time
import pytest
from dao.PlayerDao import PlayerRecord, RANK_SR_RANGES


def _player(sr=200, rank=2, mw=10, ml=5, elo=25.0, sigma=8.33, last_played=0):
    return PlayerRecord(
        guild_id="guild_123",
        player_id="p1",
        player_name="TestPlayer",
        mw=mw,
        ml=ml,
        sr=sr,
        rank=rank,
        elo=elo,
        sigma=sigma,
        last_played=last_played,
    )


class TestRpGain:
    def test_even_match_gain(self):
        p = _player()
        assert p.calculate_rp_gain(expected=0.5) == 10

    def test_underdog_win_gain(self):
        p = _player()
        assert p.calculate_rp_gain(expected=0.2) == 16

    def test_favourite_win_gain(self):
        p = _player()
        assert p.calculate_rp_gain(expected=0.8) == 4

    def test_minimum_gain_is_1(self):
        p = _player()
        assert p.calculate_rp_gain(expected=0.99) >= 1


class TestRpLoss:
    def test_even_match_loss(self):
        p = _player()
        assert p.calculate_rp_loss(expected=0.5) == -10

    def test_favourite_loss(self):
        p = _player()
        assert p.calculate_rp_loss(expected=0.8) == -16

    def test_underdog_loss(self):
        p = _player()
        assert p.calculate_rp_loss(expected=0.2) == -4

    def test_maximum_loss_is_neg_1(self):
        p = _player()
        assert p.calculate_rp_loss(expected=0.01) <= -1


class TestApplyRpChange:
    def test_win_increases_sr(self):
        p = _player(sr=200, rank=2)
        p.apply_rp_change(loss=0, expected=0.5)
        assert p.sr > 200

    def test_loss_decreases_sr(self):
        p = _player(sr=200, rank=2)
        p.apply_rp_change(loss=1, expected=0.5)
        assert p.sr < 200

    def test_sr_floor_is_zero(self):
        p = _player(sr=3, rank=0)
        p.apply_rp_change(loss=1, expected=0.5)
        assert p.sr >= 0

    def test_win_triggers_rank_up(self):
        # SR=99, rank=0 (Bronze ceiling). A win should push into Silver (rank 1).
        p = _player(sr=99, rank=0)
        p.apply_rp_change(loss=0, expected=0.5)
        assert p.rank >= 1

    def test_loss_triggers_rank_down(self):
        # SR=100, rank=1 (Silver floor). A loss pushes back to Bronze (rank 0).
        p = _player(sr=100, rank=1)
        p.apply_rp_change(loss=1, expected=0.5)
        assert p.rank == 0

    def test_delta_positive_on_win(self):
        p = _player(sr=200, rank=2)
        p.apply_rp_change(loss=0, expected=0.5)
        assert p.delta.startswith("+")

    def test_delta_negative_on_loss(self):
        p = _player(sr=200, rank=2)
        p.apply_rp_change(loss=1, expected=0.5)
        assert p.delta.startswith("-")

    def test_last_played_updated(self):
        before = int(time.time()) - 1
        p = _player()
        p.apply_rp_change(loss=0, expected=0.5)
        assert p.last_played >= before

    def test_placement_fires_on_10th_game(self):
        # Player just hit 10th game (mw+ml will equal 10 after apply_rp_change increments ml)
        # mw=9, ml=0 → after win mw=10, total=10 → placement fires
        p = _player(sr=50, rank=0, mw=9, ml=0)
        p.mw = 10  # simulate post-increment state that apply_rp_change sees
        p.ml = 0
        p.apply_rp_change(loss=0, expected=0.5)
        # Placement: rank capped at 3, sr = RANK_SR_RANGES[rank][0] + 50
        assert p.sr == RANK_SR_RANGES[p.rank][0] + 50
        assert p.rank <= 3


class TestGetEffectiveSr:
    def test_no_decay_within_grace_period(self):
        recent = int(time.time()) - (3 * 86400)  # 3 days ago, within 7-day grace
        p = _player(sr=300, last_played=recent)
        assert p.get_effective_sr() == 300.0

    def test_decay_after_grace_period(self):
        # 14 days ago → 7 days of decay at rate 10 = -70
        last = int(time.time()) - (14 * 86400)
        p = _player(sr=300, last_played=last)
        effective = p.get_effective_sr()
        assert effective < 300.0
        assert abs(effective - 230.0) < 1.0  # allow 1 SR rounding tolerance

    def test_effective_sr_floor_is_zero(self):
        last = int(time.time()) - (365 * 86400)  # 1 year inactive
        p = _player(sr=10, last_played=last)
        assert p.get_effective_sr() == 0.0

    def test_no_decay_when_last_played_is_zero(self):
        p = _player(sr=200, last_played=0)
        assert p.get_effective_sr() == 200.0

    def test_decay_commits_to_sr_on_match(self):
        # 14 days inactive → 7 days of decay at rate 10 = -70. SR before match: 300 → effective 230.
        # Win at even odds → +10. Final SR should be ~240.
        last = int(time.time()) - (14 * 86400)
        p = _player(sr=300, rank=2, last_played=last)
        p.apply_rp_change(loss=0, expected=0.5)
        assert abs(p.sr - 240.0) < 2.0
