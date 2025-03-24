from tptools.playermatch import PlayerMatch, SourcePlayerMatch

from .fixtures import *  # noqa: F403, F401


def test_playermatch_construction(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[31]
    assert pm.id == 31
    assert "planning" in pm
    assert pm["drawname"] == "Elimination 1"
    assert pm["eventname"] == "MS - 3"


def test_playermatch_status_match(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[31]
    assert pm.status == PlayerMatch.Status.MATCH


def test_playermatch_status_player(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[41]
    assert pm.status == PlayerMatch.Status.PLAYER


def test_playermatch_status_player_van_none_instead_of_zero(
    demo_playermatch_idmap,
):
    pm = demo_playermatch_idmap[54]
    assert pm.status == PlayerMatch.Status.PLAYER


def test_playermatch_status_bye(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[42]
    assert pm.status == PlayerMatch.Status.BYE


def test_playermatch_get_entry(demo_playermatch_idmap, demo_playerentry_idmap):
    pm = demo_playermatch_idmap[41]
    assert pm.get_entry(entry_getter=demo_playerentry_idmap.get)["name1"] == "Hoekmans"


def test_playermatch_get_time_unscheduled(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[40]
    assert pm.get_time() is None


def test_playermatch_get_time_scheduled(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[39]
    dt = pm.get_time()
    assert dt
    assert dt.year == 2007


def test_playermatch_get_court(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[34]
    assert pm.get_court() == "C3"


def test_playermatch_get_no_court(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[31]
    assert pm.get_court() is None


def test_playermatch_get_location(demo_playermatch_idmap):
    pm = demo_playermatch_idmap[34]
    assert pm.get_location() is None


def test_source_playermatch_status_pending(demo_playermatch_idmap):
    pm = SourcePlayerMatch(demo_playermatch_idmap[32], SourcePlayerMatch.Role.WINNER)
    assert pm.status == PlayerMatch.Status.PENDING
