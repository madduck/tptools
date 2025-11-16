import pytest

from tptools.ext.squore.feed import (
    MatchesFeed,
    MatchFeedParams,
    SquoreTournament,
)

from .conftest import MatchesFeedFactoryType


@pytest.fixture
def mf1(MatchesFeedFactory: MatchesFeedFactoryType) -> MatchesFeed:
    return MatchesFeedFactory(name="mf1")


mf1copy = mf1


def test_matches_feed_empty(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory(tournament=SquoreTournament())
    dump = mf.model_dump()
    assert "name" in dump
    assert dump.get("config") == {}
    assert dump.get("matches") == []
    assert dump.get("nummatches") == 0


def test_repr(mf1: MatchesFeed) -> None:
    assert repr(mf1) == (
        "MatchesFeed(tournament=SquoreTournament(name='Squore tournament', "
        "nentries=2, ndraws=1, ncourts=1, nmatches=2), "
        "nconfig=0)"
    )


def test_str(mf1: MatchesFeed) -> None:
    assert str(mf1) == "Squore tournament (2 entries, 1 draws, 1 courts, 2 matches)"


def test_matches_feed(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory()
    dump = mf.model_dump()
    assert "name" in dump
    assert dump.get("config") == {}
    assert dump.get("nummatches") == 2


def test_matches_feed_max_num(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory()
    dump = mf.model_dump(
        context={"matchfeedparams": MatchFeedParams(max_matches_per_court=0)}
        # TODO: ugly, as test data only has one match for one of each of two courts, but
        # the logic should be the same.
    )
    assert "name" in dump
    assert dump.get("nummatches") == 0


def test_matches_feed_with_config(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory(config={"numberOfPointsToWinGame": 15})
    dump = mf.model_dump()
    assert "numberOfPointsToWinGame" in dump["config"]


def test_tournament_to_matches_feed_court(mf1: MatchesFeed) -> None:
    dump = mf1.model_dump(
        context={
            "matchfeedparams": MatchFeedParams(court=1),
        }
    )
    assert dump["nummatches"] == 2
    found = False
    for key in dump.keys():
        if key.startswith("+"):
            assert not found, "Multiple expanded sections found"
            found = True
            assert key.endswith("C01")


@pytest.mark.parametrize("court, nummatches", [(0, 1), (1, 1), (2, 0)])
def test_tournament_to_matches_feed_onlythiscourt(
    mf1: MatchesFeed, court: int | None, nummatches: int
) -> None:
    dump = mf1.model_dump(
        context={
            "matchfeedparams": MatchFeedParams(court=court, only_this_court=True),
        }
    )
    dump.pop("config")
    dump.pop("name")
    assert dump.pop("nummatches") == nummatches
    assert len(dump) == 1
