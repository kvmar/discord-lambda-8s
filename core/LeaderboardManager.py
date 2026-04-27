from dao.LeaderboardDao import LeaderboardDao
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueRecord, QueueDao
from discord_lambda import Interaction, Components
from table2ascii import table2ascii as t2a, PresetStyle


queue_dao = QueueDao()
player_dao = PlayerDao()
leaderboard_dao = LeaderboardDao()
leaderboard_page_custom_id = "leaderboard_page"
PAGE_SIZE = 10

def build_leaderboard_rows(guild_id: str):
    player_list = player_dao.get_players_by_guild_id(guild_id)
    sorted_player_list = sorted(player_list, key=lambda x: x.sr, reverse=True)

    table = list()
    rank = 1

    for user in sorted_player_list:
        print(f"Got player: {user.player_name} with elo {user.sr}")

        if int(user.mw) + int(user.ml) < 10:
            continue

        user_data = list()
        user_data.append(rank)
        user_data.append(str(user.player_name))
        user_data.append(str(int(user.mw) + int(user.ml)))
        user_data.append(str(int(user.mw)))
        user_data.append(str(int(user.ml)))
        user_data.append(str(int(float(user.sr))))
        user_data.append(user.delta)

        table.append(user_data)
        rank += 1

    return table


def build_leaderboard_page(guild_id: str, page: int):
    table = build_leaderboard_rows(guild_id)

    total_pages = max(1, (len(table) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_rows = table[start:end]

    output = t2a(
        header=["Rank", "User", "P", "W", "L", "SR", "Change"],
        body=page_rows,
        style=PresetStyle.thin_compact
    )

    content = f"Leaderboard — Page {page + 1}/{total_pages}\n```\\n{output}\\n```"

    component = Components()
    component.add_button(
        "Previous",
        f"{leaderboard_page_custom_id}#{page - 1}",
        page <= 0,
        2
    )
    component.add_button(
        "Next",
        f"{leaderboard_page_custom_id}#{page + 1}",
        page >= total_pages - 1,
        1
    )

    return content, component


def post_leaderboard(queue_record: QueueRecord, inter: Interaction):
    print("Posting leaderboard")

    content, component = build_leaderboard_page(queue_record.guild_id, 0)

    leaderboard_record = leaderboard_dao.get_leaderboard(queue_record.guild_id)
    if len(leaderboard_record.leaderboard_message_id) > 0:
        inter.delete_message(
            message_id=leaderboard_record.leaderboard_message_id,
            channel_id=leaderboard_record.leaderboard_channel_id
        )

    resp = inter.send_message(
        content=content,
        channel_id=leaderboard_record.leaderboard_channel_id,
        components=[component]
    )

    leaderboard_record.leaderboard_message_id = resp[0]
    leaderboard_resp = leaderboard_dao.put_leaderboard(leaderboard_record)
    if leaderboard_resp is None:
        inter.delete_message(
            message_id=leaderboard_record.leaderboard_message_id,
            channel_id=leaderboard_record.leaderboard_channel_id
        )
