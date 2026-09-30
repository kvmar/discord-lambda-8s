"""Map hosts belong to match players and stay fixed across persisted views."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core import BracketManager, QueueManager, TeamManager
from core.MapHosts import assign_map_hosts, format_maps
from dao.QueueDao import QueueDao


@pytest.mark.parametrize("manual_pick", [True, False])
def test_hosts_draw_from_all_match_players_without_duplicate_captains(
    mocker, queue_record_match_ready, manual_pick
):
    record = queue_record_match_ready
    players = record.team_1 + record.team_2
    record.queue = list(players) if manual_pick else []
    record.waitlist = ["waiting_player"]
    record.maps = ["Map1", "Map1", "Map3"]
    selections = iter([players[0], players[4], players[-1]])

    def choose(eligible):
        assert set(eligible) == set(players)
        assert len(eligible) == len(players)
        return next(selections)

    mocker.patch("core.MapHosts.random.choice", side_effect=choose)
    assign_map_hosts(record)

    assert record.map_hosts == [players[0], players[4], players[-1]]
    assert format_maps(record).splitlines() == [
        f"• Map1 — Host: <@{players[0]}>",
        f"• Map1 — Host: <@{players[4]}>",
        f"• Map3 — Host: <@{players[-1]}>",
    ]


@pytest.mark.parametrize("empty_field", ["maps", "players"])
def test_empty_match_does_not_try_to_choose_a_host(mocker, queue_record_match_ready, empty_field):
    record = queue_record_match_ready
    if empty_field == "maps":
        record.maps = []
    else:
        record.queue = record.team_1 = record.team_2 = []
    choice = mocker.patch("core.MapHosts.random.choice")

    assign_map_hosts(record)

    assert record.map_hosts == []
    choice.assert_not_called()


def test_hosts_survive_database_round_trip_and_repeated_views(mocker, queue_record_match_ready):
    record = queue_record_match_ready
    record.maps = ["Map1", "Map1", "Map3"]
    record.map_hosts = ["cap1", "cap2", "user6"]
    dao = QueueDao()
    dao.table = MagicMock()
    dao.put_queue(record)
    item = dao.table.put_item.call_args.kwargs["Item"]
    restored = dao.get_queue_record_attributes(item)
    mocker.patch("core.MapHosts.random.choice", side_effect=AssertionError("Hosts must not reroll"))

    assert restored.map_hosts == record.map_hosts
    assert format_maps(restored) == format_maps(record)
    assert format_maps(restored) == format_maps(dao.get_queue_record_attributes(item))


@pytest.mark.parametrize("missing_field", [True, False])
def test_old_records_without_hosts_still_load(queue_record_match_ready, missing_field):
    item = deepcopy(queue_record_match_ready.__dict__)
    if missing_field:
        item.pop("map_hosts")
    else:
        item["map_hosts"] = None

    restored = QueueDao().get_queue_record_attributes(item)

    assert restored.map_hosts == []
    assert format_maps(restored) == "• Map1\n• Map2\n• Map3"


def test_clearing_a_match_clears_hosts_but_preserves_waitlist(queue_record_match_ready):
    record = queue_record_match_ready
    record.map_hosts = ["cap1", "cap2", "user6"]
    record.waitlist = ["next_player"]

    record.clear_queue(reset_expiry=False)

    assert record.maps == []
    assert record.map_hosts == []
    assert record.waitlist == ["next_player"]


@pytest.mark.parametrize("autopick", [False, True])
def test_start_match_saves_hosts_before_displaying_maps(
    mocker, mock_interaction, mock_player_dao, queue_record_waiting, autopick
):
    record = queue_record_waiting
    players = [f"p{i}" for i in range(8)]
    record.queue = players.copy()
    dao = mocker.patch.object(QueueManager, "queue_dao")
    dao.get_queue.return_value = record
    saved = []
    dao.put_queue.side_effect = lambda current: saved.append(deepcopy(current)) or {"ok": True}
    mocker.patch.object(QueueManager, "findMinSRDiff", return_value=players[:2])
    mocker.patch.object(QueueManager, "use_average_sr", return_value=[
        [SimpleNamespace(player_id=p) for p in players[:4]],
        [SimpleNamespace(player_id=p) for p in players[4:]],
    ])
    mocker.patch.object(QueueManager, "get_maps", return_value=["Map1", "Map2", "Map3"])
    mocker.patch("core.MapHosts.random.choice", side_effect=["p7", "p3", "p0"])

    embeds, _ = QueueManager.start_match(mock_interaction, record.queue_id, autopick)

    assert saved[0].map_hosts == ["p7", "p3", "p0"]
    for map_name, host in zip(record.maps, record.map_hosts):
        assert f"{map_name} — Host: <@{host}>" in embeds[0].desc


def test_match_found_dms_show_the_saved_hosts(mocker, queue_record_picking):
    record = queue_record_picking
    record.maps = ["Map1", "Map2", "Map3"]
    record.map_hosts = ["cap1", "user3", "cap2"]
    inter = MagicMock()
    mocker.patch("core.MapHosts.random.choice", side_effect=AssertionError("Hosts must not reroll"))

    QueueManager.send_match_found_dms(inter, record)

    assert inter.send_dm.call_count == len(record.queue)
    for call in inter.send_dm.call_args_list:
        assert call.kwargs["embeds"][0].fields[0]["value"] == format_maps(record)


@pytest.mark.parametrize("pool_button", [False, True])
def test_premade_match_saves_and_shows_hosts(
    mocker, mock_interaction, queue_record_waiting, pool_button
):
    base = queue_record_waiting
    teams = [SimpleNamespace(
        team_id=f"team{i}", team_name=f"Team {i}",
        players=[f"p{i}{j}" for j in range(4)],
        get_rating=lambda: 2000, is_ranked=lambda: False,
    ) for i in range(2)]
    team_dao = mocker.patch.object(TeamManager, "team_dao")
    team_dao.get_queued_teams.return_value = teams
    dao = MagicMock()
    dao.get_queue_or_none.return_value = base
    records = {}

    def save(record):
        records[record.queue_id] = deepcopy(record)
        return {"ok": True}

    dao.put_queue.side_effect = save
    dao.get_queue.side_effect = lambda guild_id, queue_id: deepcopy(records[queue_id])
    mocker.patch.object(TeamManager, "queue_dao", dao)
    mocker.patch.object(QueueManager, "queue_dao", dao)
    lookup = mocker.patch("dao.TeamDao.TeamDao")
    lookup.return_value.get_team.side_effect = lambda guild_id, team_id: next(
        team for team in teams if team.team_id == team_id
    )
    mocker.patch.object(TeamManager, "build_team_pool_embed", return_value=([], []))
    mocker.patch("core.MapHosts.random.choice", side_effect=["p00", "p12", "p03"])
    mock_interaction.send_response.return_value = ["message", "channel"]
    mock_interaction.send_message.return_value = ["message", "channel"]

    if pool_button:
        QueueManager.team_pool_start(mock_interaction, base.queue_id, "channel")
        message = mock_interaction.send_message.call_args
    else:
        TeamManager.start_team_match(mock_interaction)
        message = mock_interaction.send_response.call_args

    record = next(iter(records.values()))
    assert record.map_hosts == ["p00", "p12", "p03"]
    assert format_maps(record) in message.kwargs["embeds"][0].desc


def test_bracket_start_assigns_hosts_to_each_match(mocker, mock_interaction, queue_record_waiting):
    base = queue_record_waiting
    base.queue = [f"p{i}" for i in range(16)]
    mocker.patch.object(BracketManager, "_seed_teams", side_effect=lambda players, guild: [
        players[i:i + 4] for i in range(0, len(players), 4)
    ])
    mocker.patch.object(BracketManager, "_player_names", return_value="players")
    mocker.patch.object(BracketManager, "_select_map", return_value=["Map1"])
    dao = mocker.patch.object(BracketManager, "queue_dao")
    dao.get_queue.return_value = base
    dao.get_queue_or_none.return_value = None
    written = []
    dao.put_queue.side_effect = lambda record: written.append(deepcopy(record)) or {"ok": True}

    BracketManager.start_bracket(mock_interaction, base.queue_id)

    matches = [record for record in written if record.bracket_match_id]
    assert len(matches) == 2
    for match in matches:
        assert len(match.map_hosts) == 1
        assert match.map_hosts[0] in match.team_1 + match.team_2
        assert any(format_maps(match) in call.kwargs["embeds"][0].desc
                   for call in mock_interaction.send_message.call_args_list)


@pytest.mark.parametrize("reset", [False, True])
def test_grand_final_and_reset_save_hosts_for_each_map(
    mocker, mock_interaction, queue_record_match_ready, reset
):
    match = queue_record_match_ready
    match.bracket_match_id = "GF"
    meta = deepcopy(match)
    meta.tournament_id = "tournament"
    meta.bracket = {"status": "active", "result_channel_id": "results", "matches": {
        "GF": {"side": "GF", "round": 1, "status": "ready_candidate",
               "team_a": match.team_1, "team_b": match.team_2}
    }}
    dao = mocker.patch.object(BracketManager, "queue_dao")
    dao.get_queue_or_none.return_value = None
    saved = []
    dao.put_queue.side_effect = lambda record: saved.append(deepcopy(record)) or {"ok": True}
    mocker.patch.object(BracketManager, "_get_meta", return_value=meta)
    mocker.patch.object(BracketManager, "_select_map", return_value=["Map1", "Map1"])
    mocker.patch.object(BracketManager, "_player_names", return_value="players")
    mocker.patch("core.MapHosts.random.choice", side_effect=["cap1", "cap2"])

    if reset:
        BracketManager._handle_grand_final(
            mock_interaction, meta, meta.bracket, match, "GF", "B", match.team_2, match.team_1
        )
    else:
        BracketManager._maybe_post_next_wave(mock_interaction, meta.tournament_id)

    posted = saved[-1]
    assert posted.bracket_match_id == ("GF-RESET" if reset else "GF")
    assert posted.map_hosts == ["cap1", "cap2"]
    assert format_maps(posted) in mock_interaction.send_message.call_args_list[0].kwargs["embeds"][0].desc
