from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta

from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueDao, QueueRecord
from discord_lambda import Embedding, Components, Interaction
from trueskillapi import TrueSkillAccessor

queue_dao = QueueDao()
player_dao = PlayerDao()
ts = TrueSkillAccessor()

start_bracket_custom_id = "start_bracket"
bracket_a_won_custom_id = "bracket_a_won"
bracket_b_won_custom_id = "bracket_b_won"

VOTE_THRESHOLD = 3  # 3 out of 4 per-team players (lower than solo for small teams)
META_SUFFIX = "META"

# ---------------------------------------------------------------------------
# Double-elimination bracket templates for B = next power of 2.
# Each template defines nodes (match_id, side, round) and their
# pre-computed win_to / lose_to advance pointers.
# Seating uses the standard bracket pairing: [1v8, 5v4, 3v6, 7v2] for B=8,
# stored as (seed_a, seed_b) 0-indexed.
# ---------------------------------------------------------------------------

def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


# Templates keyed by B (power of 2).
# Each node: { side, round, win_to, lose_to, seed_a, seed_b }
# win_to / lose_to: {"match_id": str, "slot": "A"|"B"} or None
TEMPLATES = {
    # B=2: one WB match, loser goes straight to GF (losers bracket collapses)
    2: {
        "wb_rounds": 1,
        "lb_rounds": 0,
        "nodes": {
            "WB-R1-M0": {"side": "WB", "round": 1, "seed_a": 0, "seed_b": 1,
                          "win_to": {"match_id": "GF", "slot": "A"},
                          "lose_to": {"match_id": "GF", "slot": "B"}},
            "GF":        {"side": "GF", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to": None,
                          "lose_to": None},
        },
        "gf_match_id": "GF",
        # Standard seed order for WB-R1 matchups: [(0,1)] for B=2
        "seed_order": [(0, 1)],
    },
    # B=4: WB-R1 = 2 matches, WB-Final, LB-R1 (2 losers face off), LB-Final, GF
    4: {
        "wb_rounds": 2,
        "lb_rounds": 2,
        "nodes": {
            # WB round 1: 1v4 and 2v3 (standard seeding)
            "WB-R1-M0": {"side": "WB", "round": 1, "seed_a": 0, "seed_b": 3,
                          "win_to":  {"match_id": "WB-R2-M0", "slot": "A"},
                          "lose_to": {"match_id": "LB-R1-M0", "slot": "A"}},
            "WB-R1-M1": {"side": "WB", "round": 1, "seed_a": 1, "seed_b": 2,
                          "win_to":  {"match_id": "WB-R2-M0", "slot": "B"},
                          "lose_to": {"match_id": "LB-R1-M0", "slot": "B"}},
            # WB final
            "WB-R2-M0": {"side": "WB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "A"},
                          "lose_to": {"match_id": "LB-R2-M0", "slot": "A"}},
            # LB round 1 (the two WB-R1 losers)
            "LB-R1-M0": {"side": "LB", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R2-M0", "slot": "B"},
                          "lose_to": None},
            # LB final
            "LB-R2-M0": {"side": "LB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "B"},
                          "lose_to": None},
            "GF":        {"side": "GF", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  None,
                          "lose_to": None},
        },
        "gf_match_id": "GF",
        "seed_order": [(0, 3), (1, 2)],
    },
    # B=8: WB-R1 (4 matches), WB-R2 (2), WB-Final (1); LB-R1 (2), LB-R2 (2), LB-R3 (1), LB-R4 (1); GF
    8: {
        "wb_rounds": 3,
        "lb_rounds": 4,
        "nodes": {
            # WB round 1: seed pairing 1v8, 5v4, 3v6, 7v2
            "WB-R1-M0": {"side": "WB", "round": 1, "seed_a": 0, "seed_b": 7,
                          "win_to":  {"match_id": "WB-R2-M0", "slot": "A"},
                          "lose_to": {"match_id": "LB-R1-M0", "slot": "A"}},
            "WB-R1-M1": {"side": "WB", "round": 1, "seed_a": 4, "seed_b": 3,
                          "win_to":  {"match_id": "WB-R2-M0", "slot": "B"},
                          "lose_to": {"match_id": "LB-R1-M1", "slot": "A"}},
            "WB-R1-M2": {"side": "WB", "round": 1, "seed_a": 2, "seed_b": 5,
                          "win_to":  {"match_id": "WB-R2-M1", "slot": "A"},
                          "lose_to": {"match_id": "LB-R1-M0", "slot": "B"}},
            "WB-R1-M3": {"side": "WB", "round": 1, "seed_a": 6, "seed_b": 1,
                          "win_to":  {"match_id": "WB-R2-M1", "slot": "B"},
                          "lose_to": {"match_id": "LB-R1-M1", "slot": "B"}},
            # WB round 2
            "WB-R2-M0": {"side": "WB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "WB-R3-M0", "slot": "A"},
                          "lose_to": {"match_id": "LB-R3-M0", "slot": "A"}},
            "WB-R2-M1": {"side": "WB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "WB-R3-M0", "slot": "B"},
                          "lose_to": {"match_id": "LB-R3-M0", "slot": "B"}},
            # WB final
            "WB-R3-M0": {"side": "WB", "round": 3, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "A"},
                          "lose_to": {"match_id": "LB-R4-M0", "slot": "A"}},
            # LB round 1 (WB-R1 losers)
            "LB-R1-M0": {"side": "LB", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R2-M0", "slot": "B"},
                          "lose_to": None},
            "LB-R1-M1": {"side": "LB", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R2-M1", "slot": "B"},
                          "lose_to": None},
            # LB round 2 (LB-R1 winners face WB-R2 losers... wait)
            # Standard: LB-R2 mixes WB-R2 losers (major) with LB-R1 winners (minor)
            "LB-R2-M0": {"side": "LB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R3-M0", "slot": "B"},
                          "lose_to": None},
            "LB-R2-M1": {"side": "LB", "round": 2, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R3-M0", "slot": "B"},
                          "lose_to": None},
            # LB round 3 (LB-R2 winners face WB-R3 loser... again: major round)
            "LB-R3-M0": {"side": "LB", "round": 3, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "LB-R4-M0", "slot": "B"},
                          "lose_to": None},
            # LB final
            "LB-R4-M0": {"side": "LB", "round": 4, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "B"},
                          "lose_to": None},
            "GF":        {"side": "GF", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  None,
                          "lose_to": None},
        },
        "gf_match_id": "GF",
        "seed_order": [(0, 7), (4, 3), (2, 5), (6, 1)],
    },
    # B=16 is rare (needs 13-16 players) — define a simpler version
    16: {
        "wb_rounds": 4,
        "lb_rounds": 6,
        "nodes": {
            # WB-R1: 8 matches, standard seeding 1v16, 9v8, 5v12, 13v4, 3v14, 11v6, 7v10, 15v2
            **{f"WB-R1-M{i}": {"side": "WB", "round": 1,
                "seed_a": sa, "seed_b": sb,
                "win_to":  {"match_id": f"WB-R2-M{i//2}", "slot": "A" if i%2==0 else "B"},
                "lose_to": {"match_id": f"LB-R1-M{i}", "slot": "A"}}
               for i, (sa, sb) in enumerate(
                   [(0,15),(8,7),(4,11),(12,3),(2,13),(10,5),(6,9),(14,1)])},
            # WB-R2: 4 matches
            **{f"WB-R2-M{i}": {"side": "WB", "round": 2, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": f"WB-R3-M{i//2}", "slot": "A" if i%2==0 else "B"},
                "lose_to": {"match_id": f"LB-R3-M{i}", "slot": "A"}}
               for i in range(4)},
            # WB-R3: 2 matches
            **{f"WB-R3-M{i}": {"side": "WB", "round": 3, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": "WB-R4-M0", "slot": "A" if i==0 else "B"},
                "lose_to": {"match_id": f"LB-R5-M{i}", "slot": "A"}}
               for i in range(2)},
            # WB final
            "WB-R4-M0": {"side": "WB", "round": 4, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "A"},
                          "lose_to": {"match_id": "LB-R6-M0", "slot": "A"}},
            # LB-R1: 8 matches (WB-R1 losers play each other)
            **{f"LB-R1-M{i}": {"side": "LB", "round": 1, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": f"LB-R2-M{i//2}", "slot": "A" if i%2==0 else "B"},
                "lose_to": None}
               for i in range(8)},
            # LB-R2: 4 matches
            **{f"LB-R2-M{i}": {"side": "LB", "round": 2, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": f"LB-R3-M{i}", "slot": "B"},
                "lose_to": None}
               for i in range(4)},
            # LB-R3: 4 matches (WB-R2 losers vs LB-R2 winners)
            **{f"LB-R3-M{i}": {"side": "LB", "round": 3, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": f"LB-R4-M{i//2}", "slot": "A" if i%2==0 else "B"},
                "lose_to": None}
               for i in range(4)},
            # LB-R4: 2 matches
            **{f"LB-R4-M{i}": {"side": "LB", "round": 4, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": f"LB-R5-M{i}", "slot": "B"},
                "lose_to": None}
               for i in range(2)},
            # LB-R5: 2 matches (WB-R3 losers vs LB-R4 winners)
            **{f"LB-R5-M{i}": {"side": "LB", "round": 5, "seed_a": None, "seed_b": None,
                "win_to":  {"match_id": "LB-R6-M0", "slot": "A" if i==0 else "B"},
                "lose_to": None}
               for i in range(2)},
            # LB final
            "LB-R6-M0": {"side": "LB", "round": 6, "seed_a": None, "seed_b": None,
                          "win_to":  {"match_id": "GF", "slot": "B"},
                          "lose_to": None},
            "GF":        {"side": "GF", "round": 1, "seed_a": None, "seed_b": None,
                          "win_to":  None,
                          "lose_to": None},
        },
        "gf_match_id": "GF",
        "seed_order": [(0,15),(8,7),(4,11),(12,3),(2,13),(10,5),(6,9),(14,1)],
    },
}


# ---------------------------------------------------------------------------
# Match record helpers (stored as QueueRecords on QueueTable)
# ---------------------------------------------------------------------------

def _bracket_queue_id(tid: str, match_id: str) -> str:
    return f"BRACKET#{tid}#{match_id}"


def _meta_queue_id(tid: str) -> str:
    return f"BRACKET#{tid}#{META_SUFFIX}"


def _get_meta(guild_id: str, tid: str) -> QueueRecord:
    return queue_dao.get_queue(guild_id=guild_id, queue_id=_meta_queue_id(tid))


def _get_match(guild_id: str, tid: str, match_id: str) -> QueueRecord:
    return queue_dao.get_queue(guild_id=guild_id, queue_id=_bracket_queue_id(tid, match_id))


def _put_with_retry(record: QueueRecord, max_retries: int = 4) -> bool:
    """Write with bounded OCC retry. Returns True on success."""
    for _ in range(max_retries):
        result = queue_dao.put_queue(record)
        if result is not None:
            return True
        # OCC collision — re-read and re-apply
        refreshed = queue_dao.get_queue_or_none(record.guild_id, record.queue_id)
        if refreshed is None:
            return False
        record.version = refreshed.version
    return False


def _make_match_record(guild_id: str, tid: str, match_id: str,
                       node: dict, base: QueueRecord,
                       team_a: list, team_b: list) -> QueueRecord:
    """Create a QueueRecord representing a single bracket match."""
    expiry = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
    return QueueRecord(
        guild_id=guild_id,
        money_queue=False,
        queue_id=_bracket_queue_id(tid, match_id),
        team_1=list(team_a),
        team_2=list(team_b),
        queue=[],
        cancel_votes=[],
        team1_votes=[],
        team2_votes=[],
        maps=[],
        map_set=list(base.map_set),
        version=0,
        expiry=expiry,
        result_channel_id=base.result_channel_id,
        team_1_channel_id=base.team_1_channel_id,
        team_2_channel_id=base.team_2_channel_id,
        message_id=None,
        channel_id=None,
        channel_config={},
        waitlist=[],
        is_bracket=True,
        tournament_id=tid,
        bracket_match_id=match_id,
        bracket=None,
    )


# ---------------------------------------------------------------------------
# Embed / button builders
# ---------------------------------------------------------------------------

def _player_names(player_ids: list, guild_id: str) -> str:
    parts = []
    for pid in player_ids:
        p = player_dao.get_player(guild_id=guild_id, player_id=pid)
        if p:
            parts.append(f"• {p.get_rank_emoji()}{p.player_name}")
        else:
            parts.append(f"• <@{pid}>")
    return "\n".join(parts)


def _match_embed(match: QueueRecord, meta_bracket: dict) -> Embedding:
    mid = match.bracket_match_id
    node = meta_bracket["matches"][mid]
    side_label = {"WB": "Winners", "LB": "Losers", "GF": "Grand Final"}.get(node["side"], node["side"])
    num_maps = 2 if node["side"] == "GF" else 1
    map_str = "\n".join(f"• {m}" for m in match.maps[:num_maps]) if match.maps else "TBD"

    t1_str = _player_names(match.team_1, match.guild_id)
    t2_str = _player_names(match.team_2, match.guild_id)

    desc = (
        f"🔵 **Team A**\n{t1_str}\n\n"
        f"🔴 **Team B**\n{t2_str}\n\n"
        f"🗺️ Map{'s' if num_maps > 1 else ''}\n{map_str}"
    )
    return Embedding(
        title=f"⚔️ {side_label} — Round {node['round']} | {match.bracket_match_id}",
        desc=desc,
        color=0x7c3aed,
    )


def _match_vote_buttons(tid: str, match_id: str,
                        votes_a: int, votes_b: int) -> Components:
    comp = Components()
    comp.add_button(f"Team A Won ({votes_a})",
                    f"{bracket_a_won_custom_id}#{tid}#{match_id}", False, 1)
    comp.add_button(f"Team B Won ({votes_b})",
                    f"{bracket_b_won_custom_id}#{tid}#{match_id}", False, 4)
    return comp


def _decided_embed(match: QueueRecord, winner_side: str, meta_bracket: dict) -> Embedding:
    mid = match.bracket_match_id
    node = meta_bracket["matches"][mid]
    side_label = {"WB": "Winners", "LB": "Losers", "GF": "Grand Final"}.get(node["side"], node["side"])
    win_team = match.team_1 if winner_side == "A" else match.team_2
    lose_team = match.team_2 if winner_side == "A" else match.team_1
    winner_str = _player_names(win_team, match.guild_id)
    loser_str = _player_names(lose_team, match.guild_id)
    desc = f"🏆 **Winner — Team {'A' if winner_side == 'A' else 'B'}**\n{winner_str}\n\n❌ **Eliminated — Team {'B' if winner_side == 'A' else 'A'}**\n{loser_str}"
    return Embedding(
        title=f"✅ {side_label} — Round {node['round']} | {mid}",
        desc=desc,
        color=0x00C853,
    )


def _champion_embed(champion_ids: list, guild_id: str, tid: str) -> Embedding:
    names = _player_names(champion_ids, guild_id)
    return Embedding(
        title="🏆 Tournament Champion!",
        desc=f"Congratulations to the winners!\n\n{names}\n\n*Tournament ID: {tid}*",
        color=0xFFD700,
    )


# ---------------------------------------------------------------------------
# Bracket generation
# ---------------------------------------------------------------------------

def _seed_teams(players: list, guild_id: str) -> list:
    """Group players into 4-player teams, seed by summed get_rating() desc."""
    teams = [players[i*4:(i+1)*4] for i in range(len(players) // 4)]
    def team_rating(t):
        total = 0.0
        for pid in t:
            p = player_dao.get_player(guild_id=guild_id, player_id=pid)
            total += p.get_rating() if p else 0.0
        return total
    return sorted(teams, key=team_rating, reverse=True)


def _build_bracket_skeleton(seeds: list, template: dict) -> dict:
    """Build the bracket dict (matches skeleton + meta fields)."""
    import copy
    num_teams = len(seeds)
    nodes = copy.deepcopy(template["nodes"])

    # Assign seeds into WB-R1 slots and mark byes
    for mid, node in nodes.items():
        if node["side"] == "WB" and node["round"] == 1:
            sa = node["seed_a"]
            sb = node["seed_b"]
            node["team_a"] = seeds[sa] if sa is not None and sa < num_teams else None
            node["team_b"] = seeds[sb] if sb is not None and sb < num_teams else None

            if node["team_a"] is None or node["team_b"] is None:
                node["status"] = "bye"
            else:
                node["status"] = "ready"
        else:
            node["team_a"] = None
            node["team_b"] = None
            node["status"] = "pending"

    return nodes


def _resolve_byes(bracket_nodes: dict) -> list:
    """Auto-advance teams through bye nodes. Returns list of bye match_ids."""
    byes = []
    changed = True
    while changed:
        changed = False
        for mid, node in bracket_nodes.items():
            if node["status"] != "bye":
                continue
            # one side is real, the other is None
            real_team = node["team_a"] or node["team_b"]
            if real_team is None:
                continue
            node["status"] = "decided"
            node["winner"] = "A" if node["team_a"] else "B"
            node["win_team"] = real_team
            node["lose_team"] = []
            byes.append(mid)
            changed = True

            # advance winner
            win_ptr = node.get("win_to")
            if win_ptr:
                dst = bracket_nodes[win_ptr["match_id"]]
                slot = win_ptr["slot"]
                if slot == "A":
                    dst["team_a"] = real_team
                else:
                    dst["team_b"] = real_team
                # if both slots now filled and still pending → ready
                if dst["team_a"] and dst["team_b"] and dst["status"] == "pending":
                    dst["status"] = "ready"
    return byes


def _select_map(base: QueueRecord, num: int = 1) -> list:
    from core.QueueManager import get_maps
    all_maps = get_maps(base)
    return all_maps[:num]


# ---------------------------------------------------------------------------
# Public: start_bracket
# ---------------------------------------------------------------------------

def start_bracket(inter: Interaction, queue_id: str):
    """Called when the Start Bracket button is clicked on the queue embed."""
    base = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)

    players = list(base.queue)
    num_teams = len(players) // 4
    dropped = players[num_teams * 4:]

    if num_teams < 2:
        from discord_lambda import Embedding
        inter.send_followup(
            embeds=[Embedding(":x: Not enough players",
                              "Need at least 8 players (2 full teams of 4) to start a bracket.",
                              color=0xFF0000)],
            ephemeral=True,
        )
        return None

    random.shuffle(players)
    seeds = _seed_teams(players[:num_teams * 4], inter.guild_id)

    B = _next_pow2(num_teams)
    if B not in TEMPLATES:
        inter.send_followup(
            embeds=[Embedding(":x: Too many teams",
                              f"Brackets support up to 16 teams ({B} needed).",
                              color=0xFF0000)],
            ephemeral=True,
        )
        return None

    tid = str(uuid.uuid4())[:8]
    template = TEMPLATES[B]
    bracket_nodes = _build_bracket_skeleton(seeds, template)
    byes = _resolve_byes(bracket_nodes)

    # Build META record
    expiry = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
    meta_bracket = {
        "status": "active",
        "queue_id": queue_id,
        "result_channel_id": base.result_channel_id,
        "map_set": list(base.map_set),
        "num_teams": num_teams,
        "wb_rounds": template["wb_rounds"],
        "lb_rounds": template["lb_rounds"],
        "seeds": seeds,
        "dropped_players": dropped,
        "current_wave": 1,
        "wave_token": str(uuid.uuid4()),
        "gf_match_id": template["gf_match_id"],
        "gf_reset_match_id": None,
        "champion": None,
        "matches": bracket_nodes,
    }

    meta_record = QueueRecord(
        guild_id=inter.guild_id,
        money_queue=False,
        queue_id=_meta_queue_id(tid),
        team_1=[], team_2=[], queue=[],
        cancel_votes=[], team1_votes=[], team2_votes=[],
        maps=[], map_set=list(base.map_set),
        version=0,
        expiry=expiry,
        result_channel_id=base.result_channel_id,
        team_1_channel_id=base.team_1_channel_id,
        team_2_channel_id=base.team_2_channel_id,
        message_id=None, channel_id=None, channel_config={},
        waitlist=[],
        is_bracket=True,
        tournament_id=tid,
        bracket_match_id=None,
        bracket=meta_bracket,
    )
    queue_dao.put_queue(meta_record)

    # Create and post wave-1 match records
    wave1_matches = [mid for mid, n in bracket_nodes.items()
                     if n["status"] == "ready" and mid != template["gf_match_id"]]

    for match_id in wave1_matches:
        node = bracket_nodes[match_id]
        match_rec = _make_match_record(
            inter.guild_id, tid, match_id, node, base,
            team_a=node["team_a"], team_b=node["team_b"],
        )
        match_rec.maps = _select_map(base, 1)
        queue_dao.put_queue(match_rec)
        embed = _match_embed(match_rec, meta_bracket)
        comp = _match_vote_buttons(tid, match_id, 0, 0)
        resp = inter.send_message(
            channel_id=base.result_channel_id,
            embeds=[embed], components=[comp],
        )
        if resp:
            # store message_id so we can edit it later
            saved = queue_dao.get_queue_or_none(inter.guild_id, _bracket_queue_id(tid, match_id))
            if saved:
                saved.message_id = resp[0]
                saved.channel_id = resp[1]
                saved.channel_config = {resp[1]: resp[0]}
                queue_dao.put_queue(saved)

    # Announce bracket start
    alt_str = ""
    if dropped:
        names = ", ".join(f"<@{p}>" for p in dropped)
        alt_str = f"\n\n👥 Alternates (not enough for a full team): {names}"
    seed_lines = []
    for i, team in enumerate(seeds):
        ns = " ".join(f"<@{p}>" for p in team)
        seed_lines.append(f"**Seed {i+1}:** {ns}")
    announce = Embedding(
        title=f"🏆 Tournament Started — {queue_id}",
        desc=(
            f"{num_teams} teams, double-elimination bracket\n"
            f"{'(Byes assigned to top seeds)' if byes else ''}"
            f"{alt_str}\n\n" + "\n".join(seed_lines)
        ),
        color=0xFFD700,
    )
    inter.send_message(channel_id=base.result_channel_id, embeds=[announce])

    # Clear the originating queue and stamp it with the active bracket so the
    # queue embed can show bracket-in-progress state instead of an empty lobby.
    base.clear_queue(reset_expiry=False)
    base.is_bracket = True
    base.tournament_id = tid
    queue_dao.put_queue(base)

    # Return updated queue embed (bracket-in-progress view)
    from core.QueueManager import update_queue_embed
    return update_queue_embed(base)


# ---------------------------------------------------------------------------
# Public: report_winner (vote handler)
# ---------------------------------------------------------------------------

def report_winner(inter: Interaction, tid: str, match_id: str, side: str):
    """Handle Team A Won / Team B Won vote for a bracket match."""
    MAX_RETRIES = 4
    for attempt in range(MAX_RETRIES):
        match = queue_dao.get_queue_or_none(inter.guild_id, _bracket_queue_id(tid, match_id))
        if match is None:
            return
        # Only players in the match can vote
        if inter.user_id not in match.team_1 and inter.user_id not in match.team_2:
            inter.send_followup(
                embeds=[Embedding(":x: Not in this match", "Only players in this match can vote.", color=0xFF0000)],
                ephemeral=True,
            )
            return

        if side == "A":
            if inter.user_id not in match.team1_votes:
                match.team1_votes.append(inter.user_id)
            if inter.user_id in match.team2_votes:
                match.team2_votes.remove(inter.user_id)
        else:
            if inter.user_id not in match.team2_votes:
                match.team2_votes.append(inter.user_id)
            if inter.user_id in match.team1_votes:
                match.team1_votes.remove(inter.user_id)

        result = queue_dao.put_queue(match)
        if result is not None:
            break
    else:
        print(f"[Bracket] Vote write exhausted retries for {match_id}")
        return

    # Refresh vote counts in Discord
    meta = _get_meta(inter.guild_id, tid)
    meta_bracket = meta.bracket
    embed = _match_embed(match, meta_bracket)
    comp = _match_vote_buttons(tid, match_id, len(match.team1_votes), len(match.team2_votes))
    if match.channel_id and match.message_id:
        inter.edit_message(
            channel_id=match.channel_id, message_id=match.message_id,
            embeds=[embed], components=[comp],
        )

    # Check threshold
    win_side = None
    if len(match.team1_votes) >= VOTE_THRESHOLD:
        win_side = "A"
    elif len(match.team2_votes) >= VOTE_THRESHOLD:
        win_side = "B"

    if win_side:
        _on_match_decided(inter, tid, match_id, win_side)


def _on_match_decided(inter: Interaction, tid: str, match_id: str, winning_side: str):
    """Finalize a match result: rate, post result, advance teams."""
    # Re-read with retry to own the "decided" transition
    for attempt in range(4):
        match = queue_dao.get_queue_or_none(inter.guild_id, _bracket_queue_id(tid, match_id))
        if match is None:
            return
        # Check for idempotency: already decided by another Lambda invocation
        meta_check = _get_meta(inter.guild_id, tid)
        node_status = meta_check.bracket["matches"].get(match_id, {}).get("status")
        if node_status == "decided":
            print(f"[Bracket] {match_id} already decided, skipping")
            return

        win_team = match.team_1 if winning_side == "A" else match.team_2
        lose_team = match.team_2 if winning_side == "A" else match.team_1

        # Update ELO/SR
        ts.post_match(win_team=win_team, lose_team=lose_team, guild_id=inter.guild_id)

        # Post decided embed
        meta = _get_meta(inter.guild_id, tid)
        meta_bracket = meta.bracket
        decided_emb = _decided_embed(match, winning_side, meta_bracket)
        if match.channel_id and match.message_id:
            inter.edit_message(
                channel_id=match.channel_id, message_id=match.message_id,
                embeds=[decided_emb], components=[],
            )

        # Mark decided in meta skeleton (OCC guarded)
        node = meta_bracket["matches"][match_id]
        node["status"] = "decided"
        node["winner"] = winning_side
        node["win_team"] = win_team
        node["lose_team"] = lose_team

        gf_match_id = meta_bracket.get("gf_match_id", "GF")
        gf_reset_id = meta_bracket.get("gf_reset_match_id")

        # Special: grand final
        if match_id == gf_match_id or match_id == gf_reset_id:
            _handle_grand_final(inter, meta, meta_bracket, match, match_id, winning_side, win_team, lose_team)
            return

        # Advance winner and loser
        win_ptr = node.get("win_to")
        lose_ptr = node.get("lose_to")
        if win_ptr:
            dst_node = meta_bracket["matches"][win_ptr["match_id"]]
            if win_ptr["slot"] == "A":
                dst_node["team_a"] = win_team
            else:
                dst_node["team_b"] = win_team
            if dst_node["team_a"] and dst_node["team_b"] and dst_node["status"] == "pending":
                dst_node["status"] = "ready_candidate"
        if lose_ptr:
            dst_node = meta_bracket["matches"][lose_ptr["match_id"]]
            if lose_ptr["slot"] == "A":
                dst_node["team_a"] = lose_team
            else:
                dst_node["team_b"] = lose_team
            if dst_node["team_a"] and dst_node["team_b"] and dst_node["status"] == "pending":
                dst_node["status"] = "ready_candidate"

        result = queue_dao.put_queue(meta)
        if result is not None:
            break
    else:
        print(f"[Bracket] Meta write exhausted retries after deciding {match_id}")
        return

    _maybe_post_next_wave(inter, tid)


def _handle_grand_final(inter: Interaction, meta: QueueRecord, meta_bracket: dict,
                        match: QueueRecord, match_id: str,
                        winning_side: str, win_team: list, lose_team: list):
    """Handle GF win: immediate champion or bracket reset."""
    gf_match_id = meta_bracket.get("gf_match_id", "GF")
    gf_reset_id = meta_bracket.get("gf_reset_match_id")

    # team_1 = slot A (WB champion), team_2 = slot B (LB champion)
    wb_team = match.team_1
    lb_team = match.team_2

    if match_id == gf_match_id:
        # LB team wins game 1 → bracket reset
        if win_team == lb_team:
            reset_id = "GF-RESET"
            meta_bracket["gf_reset_match_id"] = reset_id
            meta_bracket["matches"][gf_match_id]["status"] = "decided"

            # Create reset match record
            reset_rec = _make_match_record(
                inter.guild_id, meta.tournament_id, reset_id,
                {"side": "GF", "round": 2, "win_to": None, "lose_to": None,
                 "seed_a": None, "seed_b": None, "team_a": None, "team_b": None, "status": "ready"},
                meta, wb_team, lb_team,
            )
            reset_rec.maps = _select_map(meta, 2)
            meta_bracket["matches"][reset_id] = {
                "side": "GF", "round": 2,
                "win_to": None, "lose_to": None,
                "seed_a": None, "seed_b": None,
                "team_a": wb_team, "team_b": lb_team,
                "status": "ready",
            }
            queue_dao.put_queue(meta)
            queue_dao.put_queue(reset_rec)

            embed = _match_embed(reset_rec, meta_bracket)
            comp = _match_vote_buttons(meta.tournament_id, reset_id, 0, 0)
            resp = inter.send_message(
                channel_id=meta_bracket["result_channel_id"],
                embeds=[embed], components=[comp],
            )
            if resp:
                saved = queue_dao.get_queue_or_none(inter.guild_id, _bracket_queue_id(meta.tournament_id, reset_id))
                if saved:
                    saved.message_id = resp[0]
                    saved.channel_id = resp[1]
                    saved.channel_config = {resp[1]: resp[0]}
                    queue_dao.put_queue(saved)

            reset_announce = Embedding(
                title="⚡ Bracket Reset!",
                desc="The lower-bracket team won Game 1. A deciding match will be played!",
                color=0xFF6600,
            )
            inter.send_message(channel_id=meta_bracket["result_channel_id"], embeds=[reset_announce])
            return

        # WB team wins game 1 → immediate champion
        _finish_tournament(inter, meta, meta_bracket, win_team)

    elif match_id == gf_reset_id:
        _finish_tournament(inter, meta, meta_bracket, win_team)


def _finish_tournament(inter: Interaction, meta: QueueRecord, meta_bracket: dict, champion: list):
    meta_bracket["status"] = "complete"
    meta_bracket["champion"] = champion
    queue_dao.put_queue(meta)

    embed = _champion_embed(champion, inter.guild_id, meta.tournament_id)
    inter.send_message(channel_id=meta_bracket["result_channel_id"], embeds=[embed])

    # Clear bracket flag on the originating queue so it returns to the normal lobby.
    origin_queue_id = meta_bracket.get("queue_id")
    if origin_queue_id:
        origin = queue_dao.get_queue_or_none(inter.guild_id, origin_queue_id)
        if origin and getattr(origin, "tournament_id", None) == meta.tournament_id:
            origin.is_bracket = False
            origin.tournament_id = None
            queue_dao.put_queue(origin)


def _maybe_post_next_wave(inter: Interaction, tid: str):
    """If all ready matches are decided, post the next wave of ready_candidate matches."""
    meta = _get_meta(inter.guild_id, tid)
    meta_bracket = meta.bracket

    if meta_bracket.get("status") != "active":
        return

    matches_skeleton = meta_bracket["matches"]

    # Check if any currently 'ready' (in-progress) match is not yet decided
    in_progress = [mid for mid, n in matches_skeleton.items() if n["status"] == "ready"]
    if in_progress:
        return  # still waiting on current wave

    candidates = [mid for mid, n in matches_skeleton.items() if n["status"] == "ready_candidate"]
    if not candidates:
        # Check if everything is decided → tournament might be over naturally
        undecided = [mid for mid, n in matches_skeleton.items()
                     if n["status"] not in ("decided", "bye", "pending")]
        if not undecided:
            print(f"[Bracket] Tournament {tid} appears complete.")
        return

    # Rotate wave_token to guard against double-posting
    new_token = str(uuid.uuid4())
    old_token = meta_bracket.get("wave_token")
    meta_bracket["wave_token"] = new_token
    meta_bracket["current_wave"] = meta_bracket.get("current_wave", 0) + 1

    # Promote candidates to ready
    for mid in candidates:
        matches_skeleton[mid]["status"] = "ready"

    result = queue_dao.put_queue(meta)
    if result is None:
        print(f"[Bracket] Wave token conflict — another Lambda posted next wave for {tid}")
        return

    # Re-read meta to confirm our wave_token won
    meta = _get_meta(inter.guild_id, tid)
    if meta.bracket.get("wave_token") != new_token:
        return  # lost the race

    base_map_set_record = meta  # meta has map_set

    for match_id in candidates:
        node = matches_skeleton[match_id]
        match_rec = _make_match_record(
            inter.guild_id, tid, match_id, node, base_map_set_record,
            team_a=node["team_a"], team_b=node["team_b"],
        )
        num_maps = 2 if node["side"] == "GF" else 1
        match_rec.maps = _select_map(base_map_set_record, num_maps)
        queue_dao.put_queue(match_rec)

        embed = _match_embed(match_rec, meta.bracket)
        comp = _match_vote_buttons(tid, match_id, 0, 0)
        resp = inter.send_message(
            channel_id=meta_bracket["result_channel_id"],
            embeds=[embed], components=[comp],
        )
        if resp:
            saved = queue_dao.get_queue_or_none(inter.guild_id, _bracket_queue_id(tid, match_id))
            if saved:
                saved.message_id = resp[0]
                saved.channel_id = resp[1]
                saved.channel_config = {resp[1]: resp[0]}
                queue_dao.put_queue(saved)
