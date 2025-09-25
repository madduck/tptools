import pytest

from tptools.export import Tournament
from tptools.ext.squore import (
    CourtSelectionParams,
    MatchesFeed,
)
from tptools.tpdata import TPData

from .conftest import MatchesFeedFactoryType


@pytest.fixture
def mf1(MatchesFeedFactory: MatchesFeedFactoryType) -> MatchesFeed:
    return MatchesFeedFactory(name="mf1")


mf1copy = mf1


def test_matches_feed_empty(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory(tournament=Tournament(tpdata=TPData()))
    dump = mf.model_dump()
    assert "name" in dump
    assert dump.get("config") == {}
    assert dump.get("matches") == []
    assert dump.get("nummatches") == 0


def test_repr(mf1: MatchesFeed) -> None:
    assert repr(mf1) == (
        "MatchesFeed("
        "tournament=Tournament(tpdata=TPData(name='Test 1', "
        "nentries=4, ndraws=2, ncourts=2, nmatches=2))"
        ", nconfig=0)"
    )


def test_str(mf1: MatchesFeed) -> None:
    assert str(mf1) == "Test 1 (4 entries, 2 draws, 2 courts, 2 matches)"


def test_matches_feed(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory()
    dump = mf.model_dump()
    assert "name" in dump
    assert dump.get("config") == {}
    assert dump.get("nummatches") == 2


def test_matches_feed_with_config(MatchesFeedFactory: MatchesFeedFactoryType) -> None:
    mf = MatchesFeedFactory(config={"numberOfPointsToWinGame": 15})
    dump = mf.model_dump()
    assert "numberOfPointsToWinGame" in dump["config"]


def test_tournament_to_matches_feed_court(mf1: MatchesFeed) -> None:
    dump = mf1.model_dump(
        context={
            "courtselectionparams": CourtSelectionParams(court=1),
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
            "courtselectionparams": CourtSelectionParams(
                court=court, only_this_court=True
            ),
        }
    )
    dump.pop("config")
    dump.pop("name")
    assert dump.pop("nummatches") == nummatches
    assert len(dump) == 1
