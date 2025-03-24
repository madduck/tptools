import pytest

from tptools.match import Match
from tptools.playermatch import SourcePlayerMatch

from .fixtures import *  # noqa: F403, F401


def test_match_construction_no_sources(demo_playermatch_elimination_idmap):
    Match(
        demo_playermatch_elimination_idmap[4001],
        match_getter=demo_playermatch_elimination_idmap.get,
    )


@pytest.fixture
def demo_match_elimination_idmap(
    demo_playermatch_elimination_idmap, demo_playerentry_idmap
):
    return {
        k: Match(
            v,
            match_getter=demo_playermatch_elimination_idmap.get,
            entry_getter=demo_playerentry_idmap.get,
        )
        for k, v in demo_playermatch_elimination_idmap.items()
    }


def test_match_status_player(demo_match_elimination_idmap):
    assert (
        Match.get_match_status(demo_match_elimination_idmap[5001])
        == Match.Status.PLAYER
    )


def test_match_status_bye(demo_match_elimination_idmap):
    assert (
        Match.get_match_status(demo_match_elimination_idmap[5002]) == Match.Status.BYE
    )


def test_match_status_played(demo_match_elimination_idmap):
    assert demo_match_elimination_idmap[4003].is_played()


def test_match_status_unplayed(demo_match_elimination_idmap):
    assert not demo_match_elimination_idmap[4005].is_played()


def test_match_status_not_match(demo_match_elimination_idmap):
    assert not demo_match_elimination_idmap[5001].is_match()


def test_match_status_scheduled(demo_match_elimination_idmap):
    assert demo_match_elimination_idmap[4007].is_scheduled()


def test_match_status_ready(demo_match_elimination_idmap):
    assert demo_match_elimination_idmap[4006].is_ready()


def test_match_status_not_ready(demo_match_elimination_idmap):
    assert not demo_match_elimination_idmap[3004].is_ready()


def test_match_status_won_against_bye(demo_match_elimination_idmap):
    assert (
        Match.get_match_status(demo_match_elimination_idmap[4001]) == Match.Status.BYED
    )
    assert (
        Match.get_match_status(demo_match_elimination_idmap[4008]) == Match.Status.BYED
    )


def test_match_entries_played(demo_match_elimination_idmap):
    m = demo_match_elimination_idmap[4003]
    assert m.player1["name1"] == "Bakker"
    assert m.player2["name1"] == "Schouten"


def test_match_entries_half_played(
    demo_match_elimination_idmap,
    demo_playerentry_idmap,
    demo_playermatch_elimination_idmap,
):
    m = demo_match_elimination_idmap[2003]
    assert (
        Match(m.player1, match_getter=demo_playermatch_elimination_idmap.get).status
        == Match.Status.READY
    )
    assert m.player2["name1"] == "Rood"


def test_match_entries_notplayed(
    demo_match_elimination_idmap,
    demo_playerentry_idmap,
    demo_playermatch_elimination_idmap,
):
    m = demo_match_elimination_idmap[3003]
    assert (
        Match(m.player1, match_getter=demo_playermatch_elimination_idmap.get).status
        == Match.Status.READY
    )
    assert (
        Match(m.player2, match_getter=demo_playermatch_elimination_idmap.get).status
        == Match.Status.READY
    )


@pytest.fixture(params=[4001, 4002, 4003, 4004, 4005, 4006, 4007, 4008, 3001, 3002])
def demo_match_elimination_winning_players_known(request, demo_match_elimination_idmap):
    return demo_match_elimination_idmap[request.param]


@pytest.fixture(params=[3003, 2002, 1001, 1003])
def demo_match_elimination_winning_players_unknown(
    request, demo_match_elimination_idmap
):
    return demo_match_elimination_idmap[request.param]


def test_match_elimination_winners_players_unknown(
    demo_match_elimination_winning_players_unknown,
):
    assert (
        demo_match_elimination_winning_players_unknown.player1.role
        == SourcePlayerMatch.Role.WINNER
    )
    assert (
        demo_match_elimination_winning_players_unknown.player2.role
        == SourcePlayerMatch.Role.WINNER
    )


@pytest.fixture(params=[2001, 3004])
def demo_match_elimination_winning_players_partially_known(
    request, demo_match_elimination_idmap
):
    return demo_match_elimination_idmap[request.param]


def test_match_elimination_winners_players_partially_known(
    demo_match_elimination_winning_players_partially_known,
):
    m = demo_match_elimination_winning_players_partially_known
    assert not m.is_ready()
    assert SourcePlayerMatch.Role.WINNER in (
        getattr(m._get_player(i), "role", None) for i in (0, 1)
    )


@pytest.fixture(params=[2003])
def demo_match_elimination_losing_players_partially_known(
    request, demo_match_elimination_idmap
):
    return demo_match_elimination_idmap[request.param]


def test_match_elimination_losers_players_partially_known(
    demo_match_elimination_losing_players_partially_known,
):
    m = demo_match_elimination_losing_players_partially_known
    assert not m.is_ready()
    assert SourcePlayerMatch.Role.LOSER in (
        getattr(m._get_player(i), "role", None) for i in (0, 1)
    )


@pytest.fixture(params=[2004, 1002])
def demo_match_elimination_losing_players_unknown(
    request, demo_match_elimination_idmap
):
    return demo_match_elimination_idmap[request.param]


def test_match_elimination_losers_players_unknown(
    demo_match_elimination_losing_players_unknown,
):
    assert (
        demo_match_elimination_losing_players_unknown.player1.role
        == SourcePlayerMatch.Role.LOSER
    )
    assert (
        demo_match_elimination_losing_players_unknown.player2.role
        == SourcePlayerMatch.Role.LOSER
    )


def test_match_to_dict(demo_match_elimination_idmap):
    m = demo_match_elimination_idmap[2004]
    d = m.as_dict()

    assert "matchid" in d
    assert "court" in d
    assert d["time"] is None
    assert d["status"] == "UNPLAYED"
