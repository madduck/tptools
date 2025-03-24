import pytest
from tptools.reader.csv import CSVReader

from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.draw import Draw
from tptools.tournament import Tournament


@pytest.fixture
def demo_playermatch_records():
    with open("tests/csv_fixtures/playermatches.csv", newline="") as f:
        return [PlayerMatch(r) for r in CSVReader(f)]


@pytest.fixture
def demo_playermatch_idmap(demo_playermatch_records):
    return {r["matchid"]: PlayerMatch(r) for r in demo_playermatch_records}


@pytest.fixture
def demo_playermatch_records_elimination(demo_playermatch_records):
    return [r for r in demo_playermatch_records if r["drawname"] == "Elimination 1"]


@pytest.fixture
def demo_playermatch_elimination_idmap(demo_playermatch_records_elimination):
    return {r["planning"]: PlayerMatch(r) for r in demo_playermatch_records_elimination}


@pytest.fixture
def demo_playermatch_records_rr5(demo_playermatch_records):
    return [r for r in demo_playermatch_records if r["drawname"] == "Poule 1"]


@pytest.fixture
def demo_playermatch_rr5_idmap(demo_playermatch_records_rr5):
    return {r["planning"]: PlayerMatch(r) for r in demo_playermatch_records_rr5}


@pytest.fixture
def demo_playerentry_records():
    with open("tests/csv_fixtures/playerentries.csv", newline="") as f:
        return [r for r in CSVReader(f)]


@pytest.fixture
def demo_playerentry_idmap(demo_playerentry_records):
    return {r["entryid"]: Entry(r) for r in demo_playerentry_records}


@pytest.fixture
def demo_draw_elimination(demo_playermatch_records_elimination, demo_playerentry_idmap):
    match = demo_playermatch_records_elimination[0]
    demo_draw = Draw(
        draw=match["drawname"],
        event=match["eventname"],
        entry_getter=demo_playerentry_idmap.get,
    )
    demo_draw.read_playermatches(demo_playermatch_records_elimination)
    return demo_draw


@pytest.fixture
def demo_draw_rr5(demo_playermatch_records_rr5, demo_playerentry_idmap):
    match = demo_playermatch_records_rr5[0]
    demo_draw = Draw(
        draw=match["drawname"],
        event=match["eventname"],
        entry_getter=demo_playerentry_idmap.get,
    )
    demo_draw.read_playermatches(
        demo_playermatch_records_rr5,
        entry_getter=demo_playerentry_idmap.get,
    )
    return demo_draw


@pytest.fixture
def demo_tournament(demo_playermatch_records, demo_playerentry_records):
    return Tournament(
        entries=demo_playerentry_records,
        playermatches=demo_playermatch_records,
    )
