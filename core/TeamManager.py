from __future__ import annotations

import itertools
import random

from core import QueueManager
from dao.QueueDao import QueueDao, QueueRecord
from dao.TeamDao import TeamDao, TeamRecord, MAX_TEAM_SIZE, STATUS_IDLE, STATUS_QUEUED, STATUS_IN_MATCH
from discord_lambda import Embedding
from discord_lambda import Interaction
from trueskillapi import TrueSkillAccessor

team_dao = TeamDao()
queue_dao = QueueDao()
ts = TrueSkillAccessor()

TEAM_COLOR = 0x7c3aed
ERROR_COLOR = 0xFF0000

# Match records created by the team queue use this prefix as their queue_id so
# they never collide with solo queues. '#' is reserved (custom_id delimiter),
# so the team_id fragment is appended with '-'.
TEAM_MATCH_PREFIX = "TEAM-"


def _error(title: str, desc: str) -> Embedding:
    return Embedding(title, desc, color=ERROR_COLOR)


def _mention(player_id: str) -> str:
    return f"<@{player_id}>"


# ---------------------------------------------------------------------------
# Roster embeds
# ---------------------------------------------------------------------------

def build_team_lobby_embed(team: TeamRecord) -> Embedding:
    status_label = {
        STATUS_IDLE: "🟢 Idle",
        STATUS_QUEUED: "🔎 Searching for a match",
        STATUS_IN_MATCH: "⚔️ In match",
    }.get(team.status, team.status)

    roster = ""
    for player_id in team.players:
        crown = " 👑" if player_id == team.captain_id else ""
        roster += f"• {_mention(player_id)}{crown}\n"
    for _ in range(MAX_TEAM_SIZE - len(team.players)):
        roster += "• *(empty)*\n"

    ranked = ""
    if team.is_ranked():
        ranked = f"\n{team.get_rank_emoji()} SR **{int(team.team_sr)}** • {team.tmw}W / {team.tml}L"
    else:
        played = team.tmw + team.tml
        ranked = f"\n{team.get_rank_emoji()} Unranked • {played}/10 placement games"

    embed = Embedding(
        title=f"⚔️ Team: {team.team_name}  [{len(team.players)}/{MAX_TEAM_SIZE}]",
        desc=f"{status_label}\n\n{roster}{ranked}",
        color=TEAM_COLOR,
    )
    return embed


def build_pool_board_embed(guild_id: str) -> Embedding:
    """Rendered when /queue <name> is called on a record flagged is_team_queue.
    Shows every team currently searching for a match."""
    queued = team_dao.get_queued_teams(guild_id)
    queued = sorted(queued, key=lambda t: t.get_rating(), reverse=True)

    if not queued:
        desc = ("No teams are searching right now.\n\n"
                "Captains: build a 4/4 roster with `/team_create`, `/team_add`, "
                "then `/team_queue` to join the pool.")
    else:
        rows = []
        for t in queued:
            sr = f"SR {int(t.team_sr)}" if t.is_ranked() else "Unranked"
            rows.append(f"{t.get_rank_emoji()} **{t.team_name}** — {sr} • {len(t.players)}/{MAX_TEAM_SIZE}")
        desc = ("Teams searching for a match:\n\n" + "\n".join(rows) +
                "\n\nAnyone can run `/team_start` to match the two closest teams.")

    return Embedding(title="🏟️ Team Queue Pool", desc=desc, color=TEAM_COLOR)


# ---------------------------------------------------------------------------
# Roster management (slash commands)
# ---------------------------------------------------------------------------

def create_team(guild_id: str, captain_id: str, team_name: str) -> Embedding:
    existing = team_dao.get_team_by_player(guild_id, captain_id)
    if existing is not None:
        return _error(":x: Already on a team",
                      f"You're already on **{existing.team_name}**. Leave it with `/team_leave` first.")

    team_name = (team_name or "").strip()
    if not team_name:
        return _error(":x: Invalid name", "Please provide a team name.")

    team = team_dao.new_team(guild_id, team_name, captain_id)
    team_dao.put_team(team)
    return build_team_lobby_embed(team)


def add_to_team(guild_id: str, captain_id: str, target_id: str) -> Embedding:
    team = team_dao.get_team_by_player(guild_id, captain_id)
    if team is None:
        return _error(":x: No team", "Create one first with `/team_create`.")
    if team.captain_id != captain_id:
        return _error(":x: Captain only", "Only the team captain can add players.")
    if team.status != STATUS_IDLE:
        return _error(":x: Roster locked", "You can't change the roster while searching or in a match.")
    if target_id in team.players:
        return _error(":x: Already on team", f"{_mention(target_id)} is already on **{team.team_name}**.")
    if team.is_full():
        return _error(":x: Team full", f"**{team.team_name}** already has {MAX_TEAM_SIZE} players.")

    other = team_dao.get_team_by_player(guild_id, target_id)
    if other is not None:
        return _error(":x: Already on a team", f"{_mention(target_id)} is on **{other.team_name}**.")

    team.players = team.players + [target_id]
    team_dao.put_team(team)
    return build_team_lobby_embed(team)


def kick_from_team(guild_id: str, captain_id: str, target_id: str) -> Embedding:
    team = team_dao.get_team_by_player(guild_id, captain_id)
    if team is None:
        return _error(":x: No team", "You're not on a team.")
    if team.captain_id != captain_id:
        return _error(":x: Captain only", "Only the team captain can kick players.")
    if team.status != STATUS_IDLE:
        return _error(":x: Roster locked", "You can't change the roster while searching or in a match.")
    if target_id == captain_id:
        return _error(":x: Can't kick yourself", "Use `/team_leave` to leave (and hand off captaincy).")
    if target_id not in team.players:
        return _error(":x: Not on team", f"{_mention(target_id)} isn't on **{team.team_name}**.")

    team.players = [p for p in team.players if p != target_id]
    team_dao.put_team(team)
    return build_team_lobby_embed(team)


def leave_team(guild_id: str, player_id: str) -> Embedding:
    team = team_dao.get_team_by_player(guild_id, player_id)
    if team is None:
        return _error(":x: No team", "You're not on a team.")
    if team.status == STATUS_IN_MATCH:
        return _error(":x: In a match", "You can't leave while your team is in a match.")

    team.players = [p for p in team.players if p != player_id]

    if len(team.players) == 0:
        team_dao.delete_team(guild_id, team.team_id)
        return Embedding("👋 Team disbanded",
                         f"**{team.team_name}** had no players left and was disbanded.",
                         color=TEAM_COLOR)

    # Captain left → hand captaincy to the next player and drop out of the pool.
    if player_id == team.captain_id:
        team.captain_id = team.players[0]
        if team.status == STATUS_QUEUED:
            team.status = STATUS_IDLE

    team_dao.put_team(team)
    return build_team_lobby_embed(team)


def queue_team(guild_id: str, captain_id: str) -> Embedding:
    team = team_dao.get_team_by_player(guild_id, captain_id)
    if team is None:
        return _error(":x: No team", "Create one first with `/team_create`.")
    if team.captain_id != captain_id:
        return _error(":x: Captain only", "Only the team captain can queue the team.")
    if not team.is_full():
        return _error(":x: Roster not full",
                      f"**{team.team_name}** needs {MAX_TEAM_SIZE} players to queue ({len(team.players)}/{MAX_TEAM_SIZE}).")
    if team.status == STATUS_IN_MATCH:
        return _error(":x: In a match", "Your team is already in a match.")
    if team.status == STATUS_QUEUED:
        return Embedding("🔎 Already searching",
                         f"**{team.team_name}** is already in the pool. Run `/team_start` to match.",
                         color=TEAM_COLOR)

    team.status = STATUS_QUEUED
    team_dao.put_team(team)

    pool_size = len(team_dao.get_queued_teams(guild_id))
    embed = build_team_lobby_embed(team)
    embed.add_field("Pool", f"{pool_size} team(s) searching. Run `/team_start` to match.", inline=False)
    return embed


# ---------------------------------------------------------------------------
# Matchmaking
# ---------------------------------------------------------------------------

def _pick_fairest_pair(teams: list[TeamRecord]):
    best = None
    for a, b in itertools.combinations(teams, 2):
        diff = abs(a.get_rating() - b.get_rating())
        if best is None or diff < best[0]:
            best = (diff, a, b)
    return best[1], best[2]


def start_team_match(inter: Interaction) -> None:
    """Anyone may trigger this. Matches the two closest-rated queued teams and
    posts a Match Ready message that reuses the standard vote/result flow."""
    guild_id = inter.guild_id
    queued = team_dao.get_queued_teams(guild_id)

    if len(queued) < 2:
        inter.send_response(embeds=[_error(":x: Not enough teams",
                                           f"Need at least 2 teams searching ({len(queued)} in pool).")],
                            ephemeral=True)
        return

    team_a, team_b = _pick_fairest_pair(queued)

    base = queue_dao.get_queue_or_none(guild_id, "1")
    if base is None:
        inter.send_response(embeds=[_error(":x: Queue not set up",
                                           "No base queue `1` exists to inherit channels from.")],
                            ephemeral=True)
        return

    match_queue_id = TEAM_MATCH_PREFIX + team_a.team_id[:8]
    maps = random.sample(base.map_set, min(3, len(base.map_set)))

    record = QueueRecord(
        guild_id=guild_id, money_queue=False, queue_id=match_queue_id,
        team_1=list(team_a.players), team_2=list(team_b.players), queue=list(),
        cancel_votes=list(), team1_votes=list(), team2_votes=list(),
        maps=maps, map_set=base.map_set, version=0, expiry=0,
        result_channel_id=base.result_channel_id,
        team_1_channel_id=base.team_1_channel_id, team_2_channel_id=base.team_2_channel_id,
        message_id=None, channel_id=None, channel_config={},
        waitlist=list(),
        is_team_queue=True, team_1_id=team_a.team_id, team_2_id=team_b.team_id,
    )
    record.update_expiry_date()
    queue_dao.put_queue(record)

    team_a.status = STATUS_IN_MATCH
    team_b.status = STATUS_IN_MATCH
    team_dao.put_team(team_a)
    team_dao.put_team(team_b)

    embeds, components = QueueManager.update_queue_embed(record)
    resp = inter.send_response(embeds=embeds, components=components, ephemeral=False)

    # Persist where we posted so subsequent button clicks can edit the message.
    posted = queue_dao.get_queue(guild_id, match_queue_id)
    posted.message_id = resp[0]
    posted.channel_id = resp[1]
    posted.channel_config = {resp[1]: resp[0]}
    queue_dao.put_queue(posted)


# ---------------------------------------------------------------------------
# Match completion (called from QueueManager's vote handlers)
# ---------------------------------------------------------------------------

def complete_team_match(guild_id: str, win_team_id: str, lose_team_id: str) -> None:
    """Return both teams to idle so they can re-queue. Ratings are updated
    separately by TrueSkillAccessor.post_team_match."""
    for team_id in (win_team_id, lose_team_id):
        team = team_dao.get_team(guild_id, team_id)
        if team is not None:
            team.status = STATUS_IDLE
            team_dao.put_team(team)


def cancel_team_match(guild_id: str, team_1_id: str, team_2_id: str) -> None:
    for team_id in (team_1_id, team_2_id):
        if team_id is None:
            continue
        team = team_dao.get_team(guild_id, team_id)
        if team is not None:
            team.status = STATUS_IDLE
            team_dao.put_team(team)


def _team_block(team: TeamRecord, color_dot: str) -> str:
    block = f"{color_dot} **{team.team_name}** {team.get_rank_emoji()} SR {int(team.team_sr)} ({team.team_delta})\n"
    for player_id in team.players:
        block += f"• {_mention(player_id)}\n"
    return block


def generate_team_match_done_embed(win_team_id: str, lose_team_id: str, guild_id: str) -> Embedding:
    win = team_dao.get_team(guild_id, win_team_id)
    lose = team_dao.get_team(guild_id, lose_team_id)

    desc = "🏆 **Winner**\n" + _team_block(win, "🔵") + "\n"
    desc += _team_block(lose, "🔴")

    return Embedding("✅ Team Match Completed", desc, color=TEAM_COLOR)
