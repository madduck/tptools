from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tptools.drawtype import DrawType
from tptools.match import Match
from tptools.slot import Bye, Playceholder, Slot, Unknown
from tptools.sqlmodels import (
    PlayerMatch,
    TPClub,
    TPCountry,
    TPCourt,
    TPDraw,
    TPEntry,
    TPEvent,
    TPLocation,
    TPPlayer,
    TPStage,
)
from tptools.tpdata import TPData


@pytest.fixture
def event1() -> TPEvent:
    return TPEvent(id=1, name="Herren 1", abbreviation="H1", gender=2)


@pytest.fixture
def event2() -> TPEvent:
    return TPEvent(id=2, name="Damen 1", abbreviation="D1", gender=1)


event1copy = event1


@pytest.fixture
def stage1(event1: TPEvent) -> TPStage:
    return TPStage(id=1, name="Qual", event=event1)


@pytest.fixture
def stage2(event2: TPEvent) -> TPStage:
    return TPStage(id=2, name="Main", event=event2)


stage1copy = stage1


@pytest.fixture
def draw1(stage1: TPStage) -> TPDraw:
    return TPDraw(id=1, name="Baum", type=DrawType.MONRAD, size=8, stage=stage1)


@pytest.fixture
def draw2(stage2: TPStage) -> TPDraw:
    return TPDraw(id=2, name="Gruppe", type=DrawType.GROUP, size=3, stage=stage2)


draw1copy = draw1


@pytest.fixture
def club1() -> TPClub:
    return TPClub(id=1, name="RSC")


@pytest.fixture
def club2() -> TPClub:
    return TPClub(id=2, name="SomeClub")


club1copy = club1


@pytest.fixture
def country1() -> TPCountry:
    return TPCountry(id=1, name="Holland", code="NL")


@pytest.fixture
def country2() -> TPCountry:
    return TPCountry(id=2, name="Deutschland")


country1copy = country1


@pytest.fixture
def player1(club1: TPClub, country2: TPCountry) -> TPPlayer:
    return TPPlayer(
        id=1, firstname="Martin", lastname="Krafft", club=club1, country=country2
    )


@pytest.fixture
def player2(club2: TPClub, country1: TPCountry) -> TPPlayer:
    return TPPlayer(
        id=2, firstname="Iddo", lastname="Hoeve", club=club2, country=country1
    )


player1copy = player1


@pytest.fixture
def entry1(event1: TPEvent, player1: TPPlayer) -> TPEntry:
    return TPEntry(id=1, event=event1, player1=player1)


@pytest.fixture
def entry2(event2: TPEvent, player2: TPPlayer) -> TPEntry:
    return TPEntry(id=2, event=event2, player1=player2)


entry1copy = entry1


type EntryFactoryType = Callable[[int, TPEvent, str], TPEntry]


@pytest.fixture
def EntryFactory() -> EntryFactoryType:
    def entry_maker(id: int, event: TPEvent, name: str) -> TPEntry:
        p = TPPlayer(id=id, lastname="", firstname=name)
        return TPEntry(p, event=event)

    return entry_maker


@pytest.fixture
def entry12(event1: TPEvent, player1: TPPlayer, player2: TPPlayer) -> TPEntry:
    return TPEntry(id=12, event=event1, player1=player1, player2=player2)


@pytest.fixture
def entry21(event2: TPEvent, player1: TPPlayer, player2: TPPlayer) -> TPEntry:
    return TPEntry(id=21, event=event2, player1=player2, player2=player1)


@pytest.fixture
def unknown() -> Unknown:
    return Unknown()


@pytest.fixture
def bye() -> Bye:
    return Bye()


@pytest.fixture
def winner() -> Playceholder:
    return Playceholder(matchnr=14, winner=True)


@pytest.fixture
def loser() -> Playceholder:
    return Playceholder(matchnr=14, winner=False)


@pytest.fixture
def slot1(entry1: TPEntry) -> Slot:
    return Slot(content=entry1)


@pytest.fixture
def slot2(entry2: TPEntry) -> Slot:
    return Slot(content=entry2)


@pytest.fixture
def slot21(entry21: TPEntry) -> Slot:
    return Slot(content=entry21)


@pytest.fixture
def slot12(entry12: TPEntry) -> Slot:
    return Slot(content=entry12)


@pytest.fixture
def location1() -> TPLocation:
    return TPLocation(id=1, name="Sports4You")


@pytest.fixture
def location2() -> TPLocation:
    return TPLocation(id=2, name="WeCare Germering")


location1copy = location1


@pytest.fixture
def court1(location1: TPLocation) -> TPCourt:
    return TPCourt(id=1, name="C01", location=location1)


@pytest.fixture
def court2(location2: TPLocation) -> TPCourt:
    return TPCourt(id=2, name="C07", location=location2)


court1copy = court1


type PlayerMatchFactoryType = Callable[..., PlayerMatch]


@pytest.fixture
def PlayerMatchFactory(draw1: TPDraw) -> PlayerMatchFactoryType:
    def playermatch_maker(**kwargs: Any) -> PlayerMatch:
        defaults = {
            "id": kwargs.get("planning", 1),
            "draw": draw1,
        }
        return PlayerMatch(**defaults | kwargs)

    return playermatch_maker


type PlayerFactoryType = Callable[..., PlayerMatch]


@pytest.fixture
def PlayerFactory(
    PlayerMatchFactory: PlayerMatchFactoryType, entry1: TPEntry
) -> PlayerFactoryType:
    def player_maker(**kwargs: Any) -> PlayerMatch:
        defaults = {"id": kwargs.get("planning", 1), "entry": entry1}
        enforced = {"van1": None, "van2": None, "matchnr": None}
        return PlayerMatchFactory(**defaults | kwargs | enforced)

    return player_maker


@pytest.fixture
def pmplayer1(PlayerFactory: PlayerFactoryType, entry1: TPEntry) -> PlayerMatch:
    return PlayerFactory(id=1, planning=4001, wn=3001, vn=3005, entry=entry1)


@pytest.fixture
def pmplayer2(PlayerFactory: PlayerFactoryType, entry2: TPEntry) -> PlayerMatch:
    return PlayerFactory(id=2, planning=4002, wn=3001, vn=3005, entry=entry2)


pmplayer1copy = pmplayer1


@pytest.fixture
def pmbye(PlayerFactory: PlayerFactoryType) -> PlayerMatch:
    return PlayerFactory(planning=4008, entry=None)


@pytest.fixture
def pm1(
    PlayerMatchFactory: PlayerMatchFactoryType, entry1: TPEntry, court1: TPCourt
) -> PlayerMatch:
    return PlayerMatchFactory(
        id=141,
        matchnr=14,
        entry=entry1,
        planning=3001,
        van1=4001,
        van2=4002,
        wn=2001,
        vn=2003,
        court=court1,
        time=datetime(2025, 6, 1, 11, 30),
    )


@pytest.fixture
def pm2(
    PlayerMatchFactory: PlayerMatchFactoryType,
    entry1: TPEntry,
) -> PlayerMatch:
    return PlayerMatchFactory(
        id=421,
        matchnr=42,
        entry=entry1,
        planning=2001,
        van1=3001,
        van2=3002,
        wn=1001,
        vn=1002,
    )


pm1copy = pm1


type MatchFactoryType = Callable[..., Match]


@pytest.fixture
def MatchFactory() -> MatchFactoryType:
    def match_maker(
        pm: PlayerMatch,
        entry2: TPEntry | None,
        lldiff: int,
        pldiff: int | None = None,
        iddiff: int = 1,
    ) -> Match:
        if pm.entry is not None and entry2 is not None:
            entry = entry2.model_copy(update={"event": pm.entry.event})
        else:
            entry = None
        pm2 = pm.model_copy(
            update={
                "entry": entry,
                "id": pm.id + iddiff,
                "wn": pm.wn + lldiff if pm.wn is not None else None,
                "vn": pm.vn + lldiff if pm.vn is not None else None,
                "planning": pm.planning + (lldiff if pldiff is None else pldiff),
                "winner": ((3 - pm.winner) % 3) if pm.winner is not None else None,
            }
        )
        return Match(pm1=pm, pm2=pm2)

    return match_maker


@pytest.fixture
def match1(
    MatchFactory: MatchFactoryType,
    pm1: PlayerMatch,
    entry2: TPEntry,
) -> Match:
    return MatchFactory(pm1, entry2, lldiff=4)


match1copy = match1


@pytest.fixture
def match2(
    MatchFactory: MatchFactoryType,
    pm2: PlayerMatch,
    entry2: TPEntry,
) -> Match:
    return MatchFactory(pm2, entry2, lldiff=2)


@pytest.fixture
def tpdata1(
    match1: Match,
    match2: Match,
    entry1: TPEntry,
    entry2: TPEntry,
    entry12: TPEntry,
    entry21: TPEntry,
    court1: TPCourt,
    court2: TPCourt,
    draw1: TPDraw,
    draw2: TPDraw,
) -> TPData:
    t = TPData(
        name="Test 1",
    )
    t.add_match(match1)
    t.add_match(match2)
    t.add_entry(entry1)
    t.add_entry(entry2)
    t.add_entry(entry21)
    t.add_entry(entry12)
    t.add_court(court1)
    t.add_court(court2)
    t.add_draw(draw1)
    t.add_draw(draw2)
    return t


@pytest.fixture
def tpdata2(match1: Match, entry1: TPEntry, entry2: TPEntry) -> TPData:
    t = TPData(name="Test 2")
    t.add_match(match1)
    t.add_entry(entry1)
    t.add_entry(entry2)
    return t


tpdata1copy = tpdata1
