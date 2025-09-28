from collections.abc import Callable
from contextlib import nullcontext
from typing import Any, ContextManager, Protocol

import pytest

from tptools.match import Match
from tptools.matchmaker import MatchMaker
from tptools.matchstatus import MatchStatus
from tptools.sqlmodels import TPEntry, TPPlayerMatch

from .conftest import TPMatchFactoryType, TPPlayerMatchFactoryType


def test_construction() -> None:
    _ = MatchMaker()


@pytest.fixture
def matchmaker() -> MatchMaker:
    return MatchMaker()


def test_repr(matchmaker: MatchMaker) -> None:
    assert repr(matchmaker) == "MatchMaker(nmatches=0, nunmatched=0)"


def test_str(matchmaker: MatchMaker) -> None:
    assert repr(matchmaker) == "MatchMaker(nmatches=0, nunmatched=0)"


def test_no_singles_at_start(matchmaker: MatchMaker) -> None:
    assert len(matchmaker.unmatched) == 0


def test_make_match_incomplete(matchmaker: MatchMaker, tpmatch1: Match) -> None:
    matchmaker.add_playermatch(tpmatch1.pm1)
    assert len(matchmaker.unmatched) == 1
    assert len(matchmaker.matches) == 0


def test_make_match(matchmaker: MatchMaker, tpmatch1: Match) -> None:
    matchmaker.add_playermatch(tpmatch1.pm2)
    matchmaker.add_playermatch(tpmatch1.pm1)
    assert len(matchmaker.unmatched) == 0
    assert len(matchmaker.matches) == 1
    assert matchmaker.matches.pop() == tpmatch1


def test_make_match_duplicate(matchmaker: MatchMaker, tpmatch1: Match) -> None:
    matchmaker.add_playermatch(tpmatch1.pm1)
    with pytest.raises(ValueError, match="is already registered"):
        matchmaker.add_playermatch(tpmatch1.pm1)


def test_resolve_with_unmatched(matchmaker: MatchMaker, tpmatch1: Match) -> None:
    matchmaker.add_playermatch(tpmatch1.pm1)
    with pytest.raises(AssertionError, match="Cannot resolve entries with unmatched"):
        matchmaker.resolve_match_entries()


def test_resolve_1st_round(
    matchmaker: MatchMaker,
    tpmatch1: Match,
    pmplayer1: TPPlayerMatch,
    pmplayer2: TPPlayerMatch,
) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"entry": None})
    pm2 = tpmatch1.pm2.model_copy(update={"entry": None})
    # TODO: should really mock out the Match stuff
    for pm in (pmplayer1, pmplayer2, pm1, pm2):
        matchmaker.add_playermatch(pm)
    matchmaker.resolve_match_entries()
    match = matchmaker.matches.pop()
    assert match.slot1.content == pmplayer1.entry
    assert match.slot2.content == pmplayer2.entry
    assert match.status == MatchStatus.READY


def test_resolve_1st_round_with_bye(
    matchmaker: MatchMaker,
    tpmatch1: Match,
    pmplayer1: TPPlayerMatch,
    pmbye: TPPlayerMatch,
) -> None:
    pm1 = tpmatch1.pm1.model_copy(update={"entry": None})
    pm2 = tpmatch1.pm2.model_copy(update={"entry": None})
    # TODO: should really mock out the Match stuff
    for pm in (pmplayer1, pmbye.model_copy(update={"planning": 4002}), pm1, pm2):
        matchmaker.add_playermatch(pm)
    matchmaker.resolve_match_entries()
    match = matchmaker.matches.pop()
    assert match.status == MatchStatus.READY


def test_resolve_unmatched_incomplete(matchmaker: MatchMaker, tpmatch1: Match) -> None:
    matchmaker.add_playermatch(tpmatch1.pm1)
    with pytest.raises(ValueError, match="Cannot resolve unmatched TPPlayerMatch"):
        matchmaker.resolve_unmatched()


class MatchMakerTripletFactory(Protocol):
    @classmethod
    def __call__(
        cls,
        updict1: dict[str, Any] | None = None,
        updict2: dict[str, Any] | None = None,
        updict3: dict[str, Any] | None = None,
    ) -> MatchMaker: ...


@pytest.fixture
def matchmaker_with_triplet(
    matchmaker: MatchMaker,
    tpentry1: TPEntry,
    tpentry2: TPEntry,
    pmplayer1: TPPlayerMatch,
    pmplayer2: TPPlayerMatch,
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
    TPMatchFactory: TPMatchFactoryType,
) -> MatchMakerTripletFactory:
    matchmaker.add_playermatch(pmplayer1)
    matchmaker.add_playermatch(pmplayer1.model_copy(update={"planning": 4003}))
    matchmaker.add_playermatch(pmplayer2)
    matchmaker.add_playermatch(pmplayer2.model_copy(update={"planning": 4004}))

    def matchmaker_factory(
        updict1: dict[str, Any] | None = None,
        updict2: dict[str, Any] | None = None,
        updict3: dict[str, Any] | None = None,
    ) -> MatchMaker:
        srcpm1 = TPPlayerMatchFactory(
            **{
                "matchnr": 1,
                "planning": 3001,
                "van1": 4001,
                "van2": 4002,
                "wn": 2001,
                "vn": 2003,
                "entry": None,
            }
            | (updict1 or {})
        )
        srcm1 = TPMatchFactory(srcpm1, tpentry2=None, lldiff=4)

        srcpm2 = TPPlayerMatchFactory(
            **{
                "matchnr": 2,
                "planning": 3002,
                "van1": 4003,
                "van2": 4004,
                "wn": 2001,
                "vn": 2003,
                "entry": tpentry1,
                "winner": 1,
            }
            | (updict2 or {})
        )
        srcm2 = TPMatchFactory(srcpm2, tpentry2=tpentry2, lldiff=4)
        srcpm3 = TPPlayerMatchFactory(
            **{
                "matchnr": 3,
                "planning": 2001,
                "van1": 3001,
                "van2": 3002,
                "wn": 1001,
                "vn": 1002,
            }
            | (updict3 or {})
        )
        srcm3 = TPMatchFactory(srcpm3, tpentry2=None, lldiff=2)

        for m in (srcm1, srcm2, srcm3):
            matchmaker.add_playermatch(m.pm1)
            matchmaker.add_playermatch(m.pm2)

        return matchmaker

    return matchmaker_factory


@pytest.mark.parametrize(
    "updict1, updict2, updict3, expctx",
    [
        # the case when planning matches a wn/vn of the first preceding TPPlayerMatch,
        # then we are dealing with the winner, but the match is obviously still pending.
        (
            None,
            None,
            {"planning": 2001},
            nullcontext(
                {
                    "status": lambda s: s == MatchStatus.PENDING,
                    "slot1": lambda s: str(s).startswith("Winner")
                    and str(s).endswith("#1"),
                }
            ),
        ),
        # in this (fake) case, planning is made to match wn/vn of the second preceding
        # TPPlayerMatch, then we are dealing with the loser, but the match is obviously
        # still pending.
        (
            None,
            None,
            {"planning": 2007},
            nullcontext(
                {
                    "status": lambda s: s == MatchStatus.PENDING,
                    "slot1": lambda s: str(s).startswith("Loser")
                    and str(s).endswith("#1"),
                }
            ),
        ),
        # in this case, the match's planning (2001) is not in either wn/vn of the
        # preceding matches, and that cannot be, there's an inconsistency.
        ({"wn": 2005, "vn": 2007}, None, None, pytest.raises(ValueError)),
    ],
)
def test_resolve_2nd_round_players_unknown(
    matchmaker_with_triplet: MatchMakerTripletFactory,
    updict1: dict[str, Any] | None,
    updict2: dict[str, Any] | None,
    updict3: dict[str, Any] | None,
    expctx: ContextManager[dict[str, Callable[[Any], bool]]],
) -> None:
    matchnr = 42
    matchmaker = matchmaker_with_triplet(
        updict1, updict2, (updict3 or {}) | {"matchnr": matchnr}
    )
    with expctx as exp:
        matchmaker.resolve_match_entries()

        for match in matchmaker.matches:
            if match.matchnr == matchnr:
                for key, checkfn in exp.items():
                    assert checkfn(getattr(match, key)), (
                        f"Assertion of key {key} failed"
                    )

                break


def test_resolve_unmatched_fabricate(
    matchmaker: MatchMaker,
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
) -> None:
    common = {
        "matchnr": 1,
        "van1": 3001,
        "van2": 3002,
    }
    srcpm1 = TPPlayerMatchFactory(**common | {"planning": 2001, "wn": 1001, "vn": None})
    srcpm2 = TPPlayerMatchFactory(
        **common
        | {
            "planning": 2002,
            "wn": 1003,
            "vn": 1004,
        }
    )
    pm = TPPlayerMatchFactory(matchnr=2, planning=1001, van1=2001, van2=2002)

    matchmaker.add_playermatch(srcpm1)
    matchmaker.add_playermatch(srcpm2)
    matchmaker.add_playermatch(pm)

    matchmaker.resolve_unmatched()

    assert len(matchmaker.matches) == 2
    assert len(matchmaker.unmatched) == 0


def test_resolve_unmatched_fabricate_1st_round(
    matchmaker: MatchMaker,
    pmplayer1: TPPlayerMatch,
    pmplayer2: TPPlayerMatch,
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
) -> None:
    pmplayer1 = pmplayer1.model_copy(update={"vn": None})
    pmplayer2 = pmplayer2.model_copy(update={"vn": None})

    pm = TPPlayerMatchFactory(
        matchnr=1, planning=3001, van1=pmplayer1.planning, van2=pmplayer2.planning
    )

    for p in (pmplayer1, pmplayer2, pm):
        matchmaker.add_playermatch(p)

    matchmaker.resolve_unmatched()

    assert len(matchmaker.unmatched) == 0
    assert len(matchmaker.matches) == 1
