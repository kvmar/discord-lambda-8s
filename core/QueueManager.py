from datetime import datetime

from core import LeaderboardManager
from dao.PlayerDao import PlayerDao, PlayerRecord
from dao.QueueDao import QueueDao, QueueRecord
from discord_lambda import Embedding, Interaction
from discord_lambda import Components
import random

from trueskillapi import TrueSkillAccessor

join_queue_custom_id = "join_queue"
leave_queue_custom_id = "leave_queue"
start_queue_custom_id = "start_queue"
player_pick_custom_id = "player_pick"
cancel_match_custom_id = "cancel_match"
team_1_won_custom_id = "team_1_won"
team_2_won_custom_id = "team_2_won"

queue_dao = QueueDao()
player_dao = PlayerDao()
ts = TrueSkillAccessor()

def create_queue_resources(guild_id: str):

    response = queue_dao.get_queue(guild_id, "1")
    embed = Embedding("Underworld 8s", f"Queue size: {len(response.queue)}", color=0x880808)

    print(f'Queue record: {response} for guild_id: {guild_id}')

    component = Components()
    component.add_button("Join queue", join_queue_custom_id, False, 1)
    component.add_button("Leave queue", leave_queue_custom_id, False, 4)
    component.add_button("Start queue", start_queue_custom_id, True, 3)


    response.clear_queue()

    queue_dao.put_queue(response)

    return embed, component


def add_player(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")
    if inter.user_id not in response.queue:
        response.queue.append(inter.user_id)

    resp = queue_dao.put_queue(response)

    player_data = player_dao.get_player(guild_id=inter.guild_id, player_id=inter.user_id)

    if player_data is None:
        player_dao.put_player(PlayerRecord(guild_id=inter.guild_id, player_id=inter.user_id, player_name=inter.username))

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component

    return None

def remove_player(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")

    if inter.user_id in response.queue:
        response.queue.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def start_match(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")

    caps = random.sample(response.queue, 2)
    response.team_1 = list()
    response.team_2 = list()
    response.team_1.append(caps[0])
    response.team_2.append(caps[1])

    map_picks = random.sample(response.map_set, 3)
    response.maps.append(map_picks[0])
    response.maps.append(map_picks[1])
    response.maps.append(map_picks[2])

    resp = queue_dao.put_queue(response)

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def team_1_won(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")
    if inter.user_id not in response.team_1 or inter.user_id not in response.team_2:
        return None

    if inter.user_id not in response.team1_votes:
        response.team1_votes.append(inter.user_id)

    if inter.user_id in response.team2_votes:
        response.team2_votes.remove(inter.user_id)

    if inter.user_id in response.cancel_votes:
        response.cancel_votes.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        if len(response.team1_votes) == 5:
            print(f"Posting team 1 win: {response.team_1} and team 2 lose: {response.team_2}")
            response = queue_dao.get_queue(inter.guild_id, "1")
            team1 = response.team_1
            team2 = response.team_2
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            ts.post_match(win_team=team1, lose_team=team2, guild_id=inter.guild_id)
            inter.send_message(channel_id=response.result_channel_id, embeds=[generate_match_done_embed(team1=team1, team2=team2, guild_id=inter.guild_id)])
            LeaderboardManager.post_leaderboard(queue_record=response, inter=inter)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def team_2_won(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")
    if inter.user_id not in response.team_1 or inter.user_id not in response.team_2:
        return None

    if inter.user_id not in response.team2_votes:
        response.team2_votes.append(inter.user_id)

    if inter.user_id in response.team1_votes:
        response.team1_votes.remove(inter.user_id)

    if inter.user_id in response.cancel_votes:
        response.cancel_votes.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        if len(response.team2_votes) == 5:
            print(f"Posting team 1 lose: {response.team_1} and team 2 win: {response.team_2}")
            response = queue_dao.get_queue(inter.guild_id, "1")
            team1 = response.team_1
            team2 = response.team_2
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            ts.post_match(win_team=team2, lose_team=team1, guild_id=inter.guild_id)
            inter.send_message(channel_id=response.result_channel_id, embeds=[generate_match_done_embed(team1=team1, team2=team2, guild_id=inter.guild_id)])
            LeaderboardManager.post_leaderboard(queue_record=response, inter=inter)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def generate_match_done_embed(team1, team2, guild_id):
    team_str = "Team 1:\n"
    for user in team1:
        player_data = player_dao.get_player(guild_id=guild_id, player_id=user)

        player_str = player_data.player_name + " " + str(int(float(player_data.elo) * 100)) + " (" + player_data.delta + ")\n"
        team_str = team_str + player_str

    team_str = team_str + "\nTeam 2:\n"
    for user in team2:
        player_data = player_dao.get_player(guild_id=guild_id, player_id=user)

        player_str = player_data.player_name + " " + str(int(float(player_data.elo) * 100)) + " (" + player_data.delta + ")\n"
        team_str = team_str + player_str

    return Embedding(
        "Match Result",
        f'{team_str}',
        color=0x880808,
    )

def cancel_match(inter: Interaction):
    response = queue_dao.get_queue(inter.guild_id, "1")
    if inter.user_id not in response.team_1 or inter.user_id not in response.team_2:
        return None
    
    if inter.user_id not in response.cancel_votes:
        response.cancel_votes.append(inter.user_id)

    if inter.user_id in response.team1_votes:
        response.team1_votes.remove(inter.user_id)

    if inter.user_id in response.team2_votes:
        response.team2_votes.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        if len(response.cancel_votes) > 4:
            response = queue_dao.get_queue(inter.guild_id, "1")
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def player_pick(inter: Interaction):
    player_id_inter = inter.user_id

    response = queue_dao.get_queue(inter.guild_id, "1")
    team1_pick = True
    player_pick = response.team_1[0]
    if len(response.team_1) + len(response.team_2) in (3, 4, 7):
        player_pick = response.team_2[0]
        team1_pick = False

    if player_pick != str(player_id_inter):
        return None

    player = inter.custom_id.split("#")[1]
    print(f'Picked player {player}')

    if team1_pick:
        response.team_1.append(player)
    else:
        response.team_2.append(player)

    resp = queue_dao.put_queue(response)

    if resp is not None:

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def update_queue_embed(record: QueueRecord) -> ([Embedding], [Components]):
    if len(record.team_1) == 0 or len(record.team_2) == 0:
        queue_str = ""
        for user in record.queue:
            player_data = player_dao.get_player(record.guild_id, user)
            queue_str = queue_str + player_data.player_name + "\n"

        embed = Embedding(
            "Underworld 8s",
            f'Queue size: {len(record.queue)}\n\n{queue_str}',
            color=0x880808,
        )
        component = Components()
        component.add_button("Join queue", join_queue_custom_id, False, 1)
        component.add_button("Leave queue", leave_queue_custom_id, False, 4)

        if len(record.queue) >= 8:
            component.add_button("Start queue", start_queue_custom_id, False, 3)
        else:
            component.add_button("Start queue", start_queue_custom_id, True, 3)

        return [embed], [component]
    elif len(record.team_1) != 4 or len(record.team_2) != 4:
        whose_pick = ""
        if len(record.team_1) + len(record.team_2) in (2, 5, 6):
            player_data = player_dao.get_player(record.guild_id, record.team_1[0])
            whose_pick = player_data.player_name + " its your turn to pick!"
        if len(record.team_1) + len(record.team_2) in (3, 4, 7):
            player_data = player_dao.get_player(record.guild_id, record.team_2[0])
            whose_pick = player_data.player_name + " its your turn to pick!"
        team1_str = "Team 1: \n"
        for user in record.team_1:
            player_data = player_dao.get_player(record.guild_id, user)
            team1_str = team1_str + player_data.player_name + "\n"

        team2_str = "Team 2: \n"
        for user in record.team_2:
            player_data = player_dao.get_player(record.guild_id, user)
            team2_str = team2_str + player_data.player_name + "\n"

        embed = Embedding(
            "Underworld 8s",
            f"{whose_pick}\n\n{team1_str}\n{team2_str}",
            color=0x880808,
        )

        components = get_player_pick_btns(record)
        return [embed], components
    elif len(record.team_1) == 4 and len(record.team_2) == 4:
        team1_str = "Team 1: \n"
        for user in record.team_1:
            player_data = player_dao.get_player(record.guild_id, user)
            team1_str = team1_str + player_data.player_name + "\n"

        team2_str = "Team 2: \n"
        for user in record.team_2:
            player_data = player_dao.get_player(record.guild_id, user)
            team2_str = team2_str + player_data.player_name + "\n"

        map_str = "Maps: \n"
        for map in record.maps:
            map_str = map_str + map + "\n"

        embed = Embedding(
            "Underworld 8s",
            f"{team1_str}\n{team2_str}\n{map_str}",
            color=0x880808,
        )

        component = Components()
        component.add_button(f"Team 1 Won - {len(record.team1_votes)}", team_1_won_custom_id, False, 1)
        component.add_button(f"Team 2 Won - {len(record.team2_votes)}", team_2_won_custom_id, False, 2)
        component.add_button(f"Cancel Match - {len(record.cancel_votes)}", cancel_match_custom_id, False, 4)
        return [embed], [component]



def get_player_pick_btns(record):
    cmpt_idx = 0
    queue_idx = 0

    component_list = list()
    component = Components()

    picks = record.team_1 + record.team_2

    for user in record.queue:
        player_data = player_dao.get_player(record.guild_id, user)
        if cmpt_idx == 4:
            component_list.append(component)
            component = Components()
            cmpt_idx = 0
        if user == record.team_1[0] or user == record.team_2[0]:
            print("Skipping creating a cap button")
            continue
        elif user in picks:
            component.add_button(player_data.player_name, f'{player_pick_custom_id}#{player_data.player_id}#{queue_idx}', True, 2)
        else:
            component.add_button(player_data.player_name, f'{player_pick_custom_id}#{player_data.player_id}#{queue_idx}', False, 2)
        cmpt_idx = cmpt_idx + 1
        queue_idx = queue_idx + 1

    if (cmpt_idx == 4):
        component_list.append(component)
        component = Components()
        cmpt_idx = 0

    component.add_button(f"Cancel Match - {len(record.cancel_votes)}", cancel_match_custom_id, False, 4)

    if cmpt_idx < 4:
        component_list.append(component)

    return component_list

def update_message_id(guild_id, msg_id, channel_id):
    response = queue_dao.get_queue(guild_id, "1")
    print(f'Queue record: {response} for guild_id: {guild_id}')

    response.message_id = msg_id
    response.channel_id = channel_id

    queue_dao.put_queue(response)

def update_queue_view(record: QueueRecord, embeds: list[Embedding], components: list[Components], inter: Interaction):
    curr_time = int(datetime.utcnow().timestamp())
    if  curr_time > record.expiry:
        print(f"Queue message has expired: {record.expiry} for curr_time: {curr_time}")
        record.update_expiry_date()
        queue_dao.put_queue(record)
        resp = inter.edit_response(channel_id=record.channel_id, message_id=record.message_id, embeds=embeds, components=components)
        print(f'Queue message_id: {resp}')
        update_message_id(inter.guild_id, resp[0], resp[1])
    else:
        queue_dao.put_queue(record)
        inter.send_response(components=components, embeds=embeds, ephemeral=False)