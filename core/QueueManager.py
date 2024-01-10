import itertools
from datetime import datetime

from core import LeaderboardManager
from dao.PlayerBankDao import PlayerBankRecord, PlayerBankDao
from dao.PlayerDao import PlayerDao, PlayerRecord
from dao.QueueDao import QueueDao, QueueRecord
from discord_lambda import Embedding, Interaction
from discord_lambda import Components
import random
from itertools import chain, combinations

from trueskillapi import TrueSkillAccessor
from venmoapi import VenmoApiAccessor
from more_itertools import set_partitions

join_queue_custom_id = "join_queue"
leave_queue_custom_id = "leave_queue"
start_queue_custom_id = "start_queue"
player_pick_custom_id = "player_pick"
cancel_match_custom_id = "cancel_match"
team_1_won_custom_id = "team_1_won"
team_2_won_custom_id = "team_2_won"

queue_dao = QueueDao()
player_dao = PlayerDao()
player_bank_dao = PlayerBankDao()
ts = TrueSkillAccessor()
venmo = VenmoApiAccessor()

def create_queue_resources(guild_id: str, queue_name: str):

    response = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_name)
    embed = Embedding(f"Underworld 8s {queue_name}", f"Queue size: {len(response.queue)}", color=0x880808)

    print(f'Queue record: {response} for guild_id: {guild_id}')

    component = Components()
    component.add_button("Join queue", f"join_queue_custom_id#{queue_name}", False, 1)
    component.add_button("Leave queue", f"leave_queue_custom_id#{queue_name}", False, 4)
    component.add_button("Start queue", f"start_queue_custom_id#{queue_name}", True, 3)

    response.clear_queue()

    queue_dao.put_queue(response)

    return embed, component


def add_player(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
    player_data = player_dao.get_player(guild_id=inter.guild_id, player_id=inter.user_id)

    if response.money_queue:
        if player_data is None:
            embed = Embedding("Kali 8s Bot", f"{inter.username} you must play 1 free 8s match before playing for money :smiley:", color=0x00FF00)
            inter.send_message(channel_id=response.channel_id, embeds=[embed], ephemeral=False)
            return

        player_bank_record = player_bank_dao.get_player_bank(player_id=inter.user_id)
        if player_bank_record is None:
            embed = Embedding("Kali 8s Bot", f"{player_data.player_name} register to Money 8s first using /register :smiley:", color=0x00FF00)
            inter.send_message(channel_id=response.channel_id, embeds=[embed], ephemeral=False)
            return

        if not player_bank_record.registration_complete:
            embed = Embedding("Kali 8s Bot", f"Registration still pending for user {player_data.player_name} with venmo: {player_bank_record.venmo_user}. Please accept venmo request :smiley:", color=0x00FF00)
            inter.send_message(channel_id=response.channel_id, embeds=[embed], ephemeral=False)
            return

        if player_bank_record.credits < 1:
            embed = Embedding("Kali 8s Bot", f"{player_data.player_name} you need atleast a balance of $1 to join queue :smiley:", color=0x00FF00)
            inter.send_message(channel_id=response.channel_id, embeds=[embed], ephemeral=False)
            return


    curr_time = int(datetime.utcnow().timestamp())
    if curr_time > response.expiry and len(response.team_1) == 0 and len(response.team_2) == 0:
        print("Resetting queue after 10 mins")
        response.clear_queue(reset_expiry=False)

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

def remove_player(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)

    if inter.user_id in response.queue:
        response.queue.remove(inter.user_id)

    resp = queue_dao.put_queue(response)

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def find_diff(tuple):
    sum_team_1 = 0
    idx = 0
    for i in tuple[0]:
        if idx < 4:
            sum_team_1 = sum_team_1 + i.elo
            idx = idx + 1

    idx = 0
    sum_team_2 = 0
    for i in tuple[1]:
        if idx < 4:
            sum_team_2 = sum_team_2 + i.elo
            idx = idx + 1
    return abs(sum_team_1 - sum_team_2)


def use_average_sr(response: QueueRecord):
    player_list = list()
    for player in response.queue:
        player_data = player_dao.get_player(response.guild_id, player)
        player_list.append(player_data)

    min_diff = 100000
    teams = None
    l = list(set_partitions(player_list, 2))
    for i in l:
        if len(i[0]) >= 4 and len(i[1]) >= 4:
            diff = find_diff(i)
            if diff < min_diff:
                print("Valid team" + str(i))
                print(str(diff))
                min_diff = diff
                teams = i
    print("MinDiff found: " + str(min_diff))
    return teams



def findMinSRDiff(queue: QueueRecord):
    player_list = list()
    for user in queue.queue:
        player = player_dao.get_player(guild_id=queue.guild_id, player_id=user)
        player_list.append(player)

    player_list_sorted = sorted(player_list, key= lambda x: x.elo)
    diff = 10**20

    caps = list()
    for i in range(len(player_list)-1):
        if player_list_sorted[i+1].elo - player_list_sorted[i].elo < diff:
            diff = player_list_sorted[i+1].elo - player_list_sorted[i].elo
            caps = list()
            caps.append(player_list_sorted[i+1].player_id)
            caps.append(player_list_sorted[i].player_id)

    return caps


def start_match(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)


    caps = findMinSRDiff(response)
    response.team_1 = list()
    response.team_2 = list()
    response.team_1.append(caps[0])
    response.team_2.append(caps[1])

    response.maps = list()
    map_picks = get_maps(queue_record=response)
    response.maps.append(map_picks[0])
    response.maps.append(map_picks[1])
    response.maps.append(map_picks[2])

    resp = queue_dao.put_queue(response)

    if resp is not None:
        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def get_maps(queue_record: QueueRecord):
    if "Variant" in queue_record.queue_id:
        variant_maps = ["Skidrow SND", "Invasion SND", "Terminal SND", "Highrise SND", "Karachi SND"]
        hp_maps = random.sample(queue_record.map_set, 2)
        variant_maps = random.sample(variant_maps, 2)
        variant_map_set = hp_maps + variant_maps
        map_picks = random.sample(variant_map_set, 3)
        return map_picks
    map_picks = random.sample(queue_record.map_set, 3)
    return map_picks
        



def team_1_won(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
    if inter.user_id not in response.team_1 and inter.user_id not in response.team_2:
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
            response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
            team1 = response.team_1
            team2 = response.team_2
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            ts.post_match(win_team=team1, lose_team=team2, guild_id=inter.guild_id)

            if response.money_queue:
                venmo.post_match(win_team=team1, lose_team=team2)
            inter.send_message(channel_id=response.result_channel_id, embeds=[generate_match_done_embed(team1=team1, team2=team2, guild_id=inter.guild_id, queue_record=response)])
            LeaderboardManager.post_leaderboard(queue_record=response, inter=inter)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None

def team_2_won(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
    if inter.user_id not in response.team_1 and inter.user_id not in response.team_2:
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
            response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
            team1 = response.team_1
            team2 = response.team_2
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            ts.post_match(win_team=team2, lose_team=team1, guild_id=inter.guild_id)

            if response.money_queue:
                venmo.post_match(win_team=team2, lose_team=team1, interaction=inter)
            inter.send_message(channel_id=response.result_channel_id, embeds=[generate_match_done_embed(team1=team1, team2=team2, guild_id=inter.guild_id, queue_record=response)])
            LeaderboardManager.post_leaderboard(queue_record=response, inter=inter)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def generate_match_done_embed(team1, team2, guild_id, queue_record: QueueRecord):
    team_str = "Team 1:\n"
    for user in team1:
        player_data = player_dao.get_player(guild_id=guild_id, player_id=user)
        bank_details = ""
        if queue_record.money_queue:
            player_bank_record = player_bank_dao.get_player_bank(user)
            bank_details = f" ${player_bank_record.earnings}"

        player_str = player_data.player_name + " " + str(int(float(player_data.elo) * 100)) + " (" + player_data.delta + f"){bank_details}\n"
        team_str = team_str + player_str

    team_str = team_str + "\nTeam 2:\n"
    for user in team2:
        player_data = player_dao.get_player(guild_id=guild_id, player_id=user)
        bank_details = ""
        if queue_record.money_queue:
            player_bank_record = player_bank_dao.get_player_bank(user)
            bank_details = f" ${player_bank_record.earnings}"

        player_str = player_data.player_name + " " + str(int(float(player_data.elo) * 100)) + " (" + player_data.delta + f"){bank_details}\n"
        team_str = team_str + player_str

    return Embedding(
        f"Match Result - {queue_record.queue_id}",
        f'{team_str}',
        color=0x880808,
    )

def cancel_match(inter: Interaction, queue_id: str):
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)

    if len(response.team_1) == 4 and len(response.team_2) == 4:
        if inter.user_id not in response.team_1 and inter.user_id not in response.team_2:
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
            response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
            response.clear_queue(reset_expiry=False)
            resp = queue_dao.put_queue(response)
            if resp is None:
                return None

        (embed, component) = update_queue_embed(response)

        print(f'Queue record: {response} for guild_id: {inter.guild_id}')

        return embed, component
    return None


def player_pick(inter: Interaction, queue_id: str):
    player_id_inter = inter.user_id
    response = queue_dao.get_queue(guild_id=inter.guild_id, queue_id=queue_id)
    if len(response.team_1) == 4 and len(response.team_2) == 4:
        return None

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
            f"Underworld 8s {record.queue_id}",
            f'Queue size: {len(record.queue)}\n\n{queue_str}',
            color=0x880808,
        )
        component = Components()
        component.add_button("Join queue", f"join_queue_custom_id#{record.queue_id}", False, 1)
        component.add_button("Leave queue", f"leave_queue_custom_id#{record.queue_id}", False, 4)

        if len(record.queue) >= 8:
            component.add_button("Start queue", f"start_queue_custom_id#{record.queue_id}", False, 3)
        else:
            component.add_button("Start queue", f"start_queue_custom_id#{record.queue_id}", True, 3)

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
            f"Underworld 8s {record.queue_id}",
            f"{whose_pick}\n\n{team1_str}\n{team2_str}",
            color=0x880808,
        )

        components = get_player_pick_btns(record, record.queue_id)
        return [embed], components
    elif len(record.team_1) == 4 and len(record.team_2) == 4:
        team1_str = "Team 1: \n"
        for user in record.team_1:
            player_data = player_dao.get_player(record.guild_id, user)
            team1_str = team1_str + player_data.player_name + ": " + str(int(float(player_data.elo) * 100)) + "\n"

        team2_str = "Team 2: \n"
        for user in record.team_2:
            player_data = player_dao.get_player(record.guild_id, user)
            team2_str = team2_str + player_data.player_name + ": " + str(int(float(player_data.elo) * 100)) + "\n"

        map_str = "Maps: \n"
        for map in record.maps:
            map_str = map_str + map + "\n"

        embed = Embedding(
            f"Underworld 8s {record.queue_id}",
            f"{team1_str}\n{team2_str}\n{map_str}",
            color=0x880808,
        )

        component = Components()
        component.add_button(f"Team 1 Won - {len(record.team1_votes)}", f"team_1_won_custom_id#{record.queue_id}", False, 1)
        component.add_button(f"Team 2 Won - {len(record.team2_votes)}", f"team_2_won_custom_id#{record.queue_id}", False, 2)
        component.add_button(f"Cancel Match - {len(record.cancel_votes)}", f"cancel_match_custom_id#{record.queue_id}", False, 4)
        return [embed], [component]



def get_player_pick_btns(record, queue_id: str):
    cmpt_idx = 0

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
            component.add_button(player_data.player_name, f'{player_pick_custom_id}#{player_data.player_id}#{queue_id}', True, 2)
        else:
            component.add_button(player_data.player_name, f'{player_pick_custom_id}#{player_data.player_id}#{queue_id}', False, 2)
        cmpt_idx = cmpt_idx + 1

    if (cmpt_idx == 4):
        component_list.append(component)
        component = Components()
        cmpt_idx = 0

    component.add_button(f"Cancel Match - {len(record.cancel_votes)}", f"cancel_match_custom_id#{record.queue_id}", False, 4)

    if cmpt_idx < 4:
        component_list.append(component)

    return component_list

def update_message_id(guild_id, msg_id, channel_id, queue_id):
    response = queue_dao.get_queue(guild_id=guild_id, queue_id=queue_id)
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
        update_message_id(inter.guild_id, resp[0], resp[1], record.queue_id)
    else:
        queue_dao.put_queue(record)
        inter.send_response(components=components, embeds=embeds, ephemeral=False)