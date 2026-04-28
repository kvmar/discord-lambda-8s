from dao.LeaderboardDao import LeaderboardDao
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction, Components
from discord_lambda.Interaction import Embedding


queue_dao = QueueDao()
player_dao = PlayerDao()
leaderboard_dao = LeaderboardDao()
leaderboard_page_custom_id = "leaderboard_page"
PAGE_SIZE = 10

MEDAL_EMOJIS = {1: "🥇", 2: "🥈", 3: "🥉"}
LEADERBOARD_COLOR = 0xFFD700  # Gold


def build_leaderboard_entries(guild_id: str):
    player_list = player_dao.get_players_by_guild_id(guild_id)
    sorted_player_list = sorted(player_list, key=lambda x: x.sr, reverse=True)

    entries = []
    rank = 1

    for user in sorted_player_list:
        print(f"Got player: {user.player_name} with SR {user.sr}")

        if int(user.mw) + int(user.ml) < 10:
            continue

        medal = MEDAL_EMOJIS.get(rank, f"`#{rank}`")
        rank_emoji = user.get_rank_emoji()
        streak_emoji = user.get_streak()
        sr = int(float(user.sr))
        delta = user.delta if (user.delta.startswith("+") or user.delta.startswith("-")) else f"+{user.delta}"
        wins = int(user.mw)
        losses = int(user.ml)
        total_games = wins + losses

        entry = {
            "medal": medal,
            "rank_emoji": rank_emoji,
            "streak_emoji": streak_emoji,
            "name": user.player_name,
            "sr": sr,
            "delta": delta,
            "wins": wins,
            "losses": losses,
            "total": total_games
        }
        entries.append(entry)
        rank += 1

    return entries


def build_leaderboard_page(guild_id: str, page: int):
    entries = build_leaderboard_entries(guild_id)

    total_pages = max(1, (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_entries = entries[start:end]

    rows = []
    for entry in page_entries:
        streak = f" {entry['streak_emoji']}" if entry['streak_emoji'] else ""
        row = (
            f"{entry['medal']} {entry['rank_emoji']} **{entry['name']}**{streak}"
            f"  •  SR: **{entry['sr']}** ({entry['delta']})  •  {entry['wins']}W / {entry['losses']}L"
        )
        rows.append(row)

    description = "\n".join(rows) if rows else "No players with 10+ games yet. Keep playing!"

    embed = Embedding(
        title="🏆  Season Leaderboard",
        desc=description,
        color=LEADERBOARD_COLOR,
    )
    embed.set_footer(text=f"Page {page + 1}/{total_pages}  •  10 games required to place")

    component = Components()
    component.add_button(
        "◀ Previous",
        f"{leaderboard_page_custom_id}#{page - 1}",
        page <= 0,
        2
    )
    component.add_button(
        "Next ▶",
        f"{leaderboard_page_custom_id}#{page + 1}",
        page >= total_pages - 1,
        1
    )

    return embed, component


def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    """Called automatically after a game ends — refreshes the pinned leaderboard message."""
    print("Posting leaderboard")

    embed, component = build_leaderboard_page(queue_record.guild_id, 0)

    leaderboard_record = leaderboard_dao.get_leaderboard(queue_record.guild_id)
    if len(leaderboard_record.leaderboard_message_id) > 0:
        inter.delete_message(
            message_id=leaderboard_record.leaderboard_message_id,
            channel_id=leaderboard_record.leaderboard_channel_id
        )

    resp = inter.send_message(
        content=None,
        embeds=[embed],
        components=[component],
        channel_id=leaderboard_record.leaderboard_channel_id
    )

    # If conditional write thrown then delete message
    leaderboard_record.leaderboard_message_id = resp[0]
    leaderboard_resp = leaderboard_dao.put_leaderboard(leaderboard_record)
    if leaderboard_resp is None:
        inter.delete_message(
            message_id=leaderboard_record.leaderboard_message_id,
            channel_id=leaderboard_record.leaderboard_channel_id
        )
