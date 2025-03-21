from tptools.entry import Entry

from .fixtures import *  # noqa: F403, F401


def test_entry_construction(demo_playerentry_records):
    e = Entry(demo_playerentry_records[0])
    assert "player1id" in e
    assert e["firstname1"] == "Erik"
    assert e["entryid"] == 1
    assert e["player1id"] == 1
    assert e["club1"] == "Limmen"
    assert e["country1"] == "CAN"


def test_entry_players(demo_playerentry_records):
    e = Entry(demo_playerentry_records[0])
    assert e.players == ("Erik Hansen",)


def test_entry_players_short(demo_playerentry_records):
    e = Entry(demo_playerentry_records[0])
    assert e.get_players(short=True) == ("E.Hansen",)


def test_entry_playername_doubles(demo_playerentry_records):
    e = Entry(demo_playerentry_records[6])
    assert e.players == ("Patrick Rood", "Diederik Voort")


def test_entry_players_doubles_short(demo_playerentry_records):
    e = Entry(demo_playerentry_records[6])
    assert e.get_players(short=True) == ("P.Rood", "D.Voort")


def test_entry_country(demo_playerentry_records):
    e = Entry(demo_playerentry_records[0])
    assert e.countries == ("CAN",)


def test_entry_country_empty(demo_playerentry_records):
    e = Entry(demo_playerentry_records[13])
    assert e.countries == (None,)


def test_entry_country_doubles(demo_playerentry_records):
    e = Entry(demo_playerentry_records[6])
    assert e.countries == ("USA", "NED")


def test_entry_country_doubles_same(demo_playerentry_records):
    e = Entry(demo_playerentry_records[8])
    assert e.countries == ("USA", "USA")


def test_entry_club(demo_playerentry_records):
    e = Entry(demo_playerentry_records[0])
    assert e.clubs == ("Limmen",)


def test_entry_club_empty(demo_playerentry_records):
    e = Entry(demo_playerentry_records[16])
    assert e.clubs == (None,)


def test_entry_club_doubles(demo_playerentry_records):
    e = Entry(demo_playerentry_records[6])
    assert e.clubs == ("Egmond", "Hogedijk")


def test_entry_club_doubles_same(demo_playerentry_records):
    e = Entry(demo_playerentry_records[8])
    assert e.clubs == ("Egmond", "Egmond")


def test_make_team_name():
    assert Entry.make_team_name(("A", "B")) == "A&B"


def test_make_team_name_joinstr():
    joinstr = "/"
    assert Entry.make_team_name(("A", "B"), joinstr=joinstr) == f"A{joinstr}B"


def test_make_team_name_single():
    assert Entry.make_team_name(("A",)) == "A"


def test_make_team_name_same():
    assert Entry.make_team_name(("A", "A")) == "A"


def test_entry_sort_singles(demo_playerentry_records):
    e1 = Entry(demo_playerentry_records[4])
    e2 = Entry(demo_playerentry_records[5])
    assert e1 < e2
    assert not e1 >= e2


def test_entry_sort_doubles(demo_playerentry_records):
    e1 = Entry(demo_playerentry_records[12])
    e2 = Entry(demo_playerentry_records[13])
    assert e1 < e2
    assert not e1 >= e2


def test_entry_sort_same(demo_playerentry_records):
    e1 = Entry(demo_playerentry_records[1])
    e2 = Entry(demo_playerentry_records[2])
    assert not e1 < e2
    assert e1 >= e2
    assert e1 == e2
