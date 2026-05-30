from dao.LeaderboardDao import LeaderboardDao
from dao.TeamDao import TeamDao
from discord_lambda import Components
from discord_lambda.Interaction import Embedding

team_dao = TeamDao()
leaderboard_dao = LeaderboardDao()

team_leaderboard_page_custom_id = "team_leaderboard_page"
PAGE_SIZE = 10

MEDAL_EMOJIS = {1: "🥇", 2: "🥈", 3: "🥉"}
LEADERBOARD_COLOR = 0x7c3aed


def build_team_leaderboard_entries(guild_id: str):
    teams = team_dao.get_teams_by_guild_id(guild_id)
    sorted_teams = sorted(teams, key=lambda t: t.team_sr, reverse=True)

    entries = []
    rank = 1
    for team in sorted_teams:
        if (int(team.tmw) + int(team.tml)) < 1:
            continue

        medal = MEDAL_EMOJIS.get(rank, f"`#{rank}`")
        delta = team.team_delta if (team.team_delta.startswith("+") or team.team_delta.startswith("-")) else f"+{team.team_delta}"
        entries.append({
            "medal": medal,
            "rank_emoji": team.get_rank_emoji(),
            "name": team.team_name,
            "sr": int(team.team_sr),
            "delta": delta,
            "wins": int(team.tmw),
            "losses": int(team.tml),
        })
        rank += 1

    return entries


def build_team_leaderboard_page(guild_id: str, page: int):
    entries = build_team_leaderboard_entries(guild_id)

    total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    page_entries = entries[start:start + PAGE_SIZE]

    rows = []
    for entry in page_entries:
        rows.append(
            f"{entry['medal']} {entry['rank_emoji']} **{entry['name']}**\n"
            f"└─ SR: **{entry['sr']}** ({entry['delta']}) | {entry['wins']}W / {entry['losses']}L"
        )

    description = "\n".join(rows) if rows else "No team matches completed yet. Keep playing!"

    embed = Embedding(
        title="🏆 Team Leaderboard",
        desc=description,
        color=LEADERBOARD_COLOR,
    )
    embed.set_footer(text=f"Page {page + 1}/{total_pages}  •  Ranked after first match")

    component = Components()
    component.add_button("◀ Previous", f"{team_leaderboard_page_custom_id}#{page - 1}", page <= 0, 2)
    component.add_button("Next ▶", f"{team_leaderboard_page_custom_id}#{page + 1}", page >= total_pages - 1, 1)

    return embed, component


def post_team_leaderboard(guild_id: str, inter) -> None:
    """Called automatically after a team match ends — refreshes the pinned team
    leaderboard message. Silently skips if no team leaderboard channel is set."""
    record = leaderboard_dao.get_leaderboard(guild_id)
    if not record.team_leaderboard_channel_id:
        print("No team leaderboard channel configured, skipping post")
        return

    embed, component = build_team_leaderboard_page(guild_id, 0)

    if record.team_leaderboard_message_id:
        inter.delete_message(
            message_id=record.team_leaderboard_message_id,
            channel_id=record.team_leaderboard_channel_id,
        )

    resp = inter.send_message(
        channel_id=record.team_leaderboard_channel_id,
        embeds=[embed],
        components=[component],
    )

    record.team_leaderboard_message_id = resp[0]
    leaderboard_resp = leaderboard_dao.put_leaderboard(record)
    if leaderboard_resp is None:
        inter.delete_message(
            message_id=record.team_leaderboard_message_id,
            channel_id=record.team_leaderboard_channel_id,
        )
