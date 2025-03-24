from tptools.draw import Draw

from .fixtures import *  # noqa: F403, F401


def test_draw_construction_noname():
    draw = Draw()
    assert draw.name is None


def test_draw_construction_nameonlydraw():
    draw = Draw(draw="Herren 1")
    assert draw.name == "Herren 1"


def test_draw_construction_namesame():
    draw = Draw(event="Herren 1", draw="Herren 1")
    assert draw.name == "Herren 1"


def test_draw_construction_namefull():
    draw = Draw(event="Herren 1", draw="Group A")
    assert draw.name == "Herren 1, Group A"


def test_draw_treewalk_elimination(demo_draw_elimination):
    assert len(demo_draw_elimination.players) == 14
    assert len(demo_draw_elimination.byes) == 2
    assert len(demo_draw_elimination.matches) == 16


def test_draw_get_upcoming_matches_elimination(demo_draw_elimination):
    assert len(list(demo_draw_elimination.get_matches())) == 4


def test_draw_get_matches_ready_elimination(demo_draw_elimination):
    assert len(list(demo_draw_elimination.get_matches(include_not_ready=False))) == 4


def test_draw_get_matches_with_not_ready_elimination(demo_draw_elimination):
    assert len(list(demo_draw_elimination.get_matches(include_not_ready=True))) == 10


def test_draw_get_matches_with_played_elimination(demo_draw_elimination):
    assert len(list(demo_draw_elimination.get_matches(include_played=True))) == 4


def test_draw_treewalk_rr5(demo_draw_rr5):
    assert len(demo_draw_rr5.players) == 5
    assert len(demo_draw_rr5.byes) == 0
    assert len(demo_draw_rr5.matches) == 10


def test_draw_get_upcoming_matches_rr5(demo_draw_rr5):
    assert len(list(demo_draw_rr5.get_matches())) == 4


def test_draw_get_matches_ready_rr5(demo_draw_rr5):
    assert len(list(demo_draw_rr5.get_matches(include_not_ready=False))) == 4


def test_draw_get_matches_with_not_ready_rr5(demo_draw_rr5):
    assert len(list(demo_draw_rr5.get_matches(include_not_ready=True))) == 8


def test_draw_get_matches_with_played_rr5(demo_draw_rr5):
    assert len(list(demo_draw_rr5.get_matches(include_played=True))) == 4
