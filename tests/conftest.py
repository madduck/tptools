from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tptools import Court, Draw, Entry, Match, Tournament
from tptools.drawtype import DrawType
from tptools.entry import Club, Country, Player
from tptools.slot import Bye, Playceholder, Slot, Unknown
from tptools.sqlmodels import (
    TPClub,
    TPCountry,
    TPCourt,
    TPDraw,
    TPEntry,
    TPEvent,
    TPLocation,
    TPPlayer,
    TPPlayerMatch,
    TPStage,
)
from tptools.tpmatch import TPMatch


@pytest.fixture
def tpevent1() -> TPEvent:
    return TPEvent(id=1, name="Herren 1", abbreviation="H1", gender=2)


@pytest.fixture
def tpevent2() -> TPEvent:
    return TPEvent(id=2, name="Damen 1", abbreviation="D1", gender=1)


tpevent1copy = tpevent1


@pytest.fixture
def tpstage1(tpevent1: TPEvent) -> TPStage:
    return TPStage(id=1, name="Qual", event=tpevent1)


@pytest.fixture
def tpstage2(tpevent2: TPEvent) -> TPStage:
    return TPStage(id=2, name="Main", event=tpevent2)


tpstage1copy = tpstage1


@pytest.fixture
def tpdraw1(tpstage1: TPStage) -> TPDraw:
    return TPDraw(id=1, name="Baum", type=DrawType.MONRAD, size=8, stage=tpstage1)


@pytest.fixture
def tpdraw2(tpstage2: TPStage) -> TPDraw:
    return TPDraw(id=2, name="Gruppe", type=DrawType.GROUP, size=3, stage=tpstage2)


tpdraw1copy = tpdraw1


@pytest.fixture
def draw1(tpdraw1: TPDraw) -> Draw:
    return Draw.from_tp_model(tpdraw1)


@pytest.fixture
def draw2(tpdraw2: TPDraw) -> Draw:
    return Draw.from_tp_model(tpdraw2)


draw1copy = draw1


@pytest.fixture
def tpclub1() -> TPClub:
    return TPClub(id=1, name="RSC")


@pytest.fixture
def tpclub2() -> TPClub:
    return TPClub(id=2, name="SomeClub")


tpclub1copy = tpclub1


@pytest.fixture
def club1(tpclub1: TPClub) -> Club:
    return Club.from_tp_model(tpclub1)


@pytest.fixture
def tpcountry1() -> TPCountry:
    return TPCountry(id=1, name="Holland", code="NL")


@pytest.fixture
def tpcountry2() -> TPCountry:
    return TPCountry(id=2, name="Deutschland")


tpcountry1copy = tpcountry1


@pytest.fixture
def country1(tpcountry1: TPCountry) -> Country:
    return Country.from_tp_model(tpcountry1)


@pytest.fixture
def country2(tpcountry2: TPCountry) -> Country:
    return Country.from_tp_model(tpcountry2)


@pytest.fixture
def tpplayer1(tpclub1: TPClub, tpcountry2: TPCountry) -> TPPlayer:
    return TPPlayer(
        id=1, firstname="Martin", lastname="Krafft", club=tpclub1, country=tpcountry2
    )


@pytest.fixture
def tpplayer2(tpclub2: TPClub, tpcountry1: TPCountry) -> TPPlayer:
    return TPPlayer(
        id=2, firstname="Iddo", lastname="Hoeve", club=tpclub2, country=tpcountry1
    )


tpplayer1copy = tpplayer1


@pytest.fixture
def player1(tpplayer1: TPPlayer) -> Player:
    return Player.from_tp_model(tpplayer1)


@pytest.fixture
def tpentry1(tpevent1: TPEvent, tpplayer1: TPPlayer) -> TPEntry:
    return TPEntry(id=1, event=tpevent1, player1=tpplayer1)


@pytest.fixture
def tpentry2(tpevent2: TPEvent, tpplayer2: TPPlayer) -> TPEntry:
    return TPEntry(id=2, event=tpevent2, player1=tpplayer2)


tpentry1copy = tpentry1


type EntryFactoryType = Callable[[int, TPEvent, str], TPEntry]


@pytest.fixture
def EntryFactory() -> EntryFactoryType:
    def entry_maker(id: int, event: TPEvent, name: str) -> TPEntry:
        p = TPPlayer(id=id, lastname="", firstname=name)
        return TPEntry(event=event, player1=p)

    return entry_maker


@pytest.fixture
def tpentry12(tpevent1: TPEvent, tpplayer1: TPPlayer, tpplayer2: TPPlayer) -> TPEntry:
    return TPEntry(id=12, event=tpevent1, player1=tpplayer1, player2=tpplayer2)


@pytest.fixture
def tpentry21(tpevent2: TPEvent, tpplayer1: TPPlayer, tpplayer2: TPPlayer) -> TPEntry:
    return TPEntry(id=21, event=tpevent2, player1=tpplayer2, player2=tpplayer1)


@pytest.fixture
def entry1(tpentry1: TPEntry) -> Entry:
    return Entry.from_tp_model(tpentry1)


@pytest.fixture
def entry2(tpentry2: TPEntry) -> Entry:
    return Entry.from_tp_model(tpentry2)


entry1copy = entry1


@pytest.fixture
def entry12(tpentry12: TPEntry) -> Entry:
    return Entry.from_tp_model(tpentry12)


@pytest.fixture
def entry21(tpentry21: TPEntry) -> Entry:
    return Entry.from_tp_model(tpentry21)


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
def slot1(tpentry1: TPEntry) -> Slot:
    return Slot(content=tpentry1)


@pytest.fixture
def slot2(tpentry2: TPEntry) -> Slot:
    return Slot(content=tpentry2)


@pytest.fixture
def slot21(tpentry21: TPEntry) -> Slot:
    return Slot(content=tpentry21)


@pytest.fixture
def slot12(tpentry12: TPEntry) -> Slot:
    return Slot(content=tpentry12)


@pytest.fixture
def tplocation1() -> TPLocation:
    return TPLocation(id=1, name="Sports4You")


@pytest.fixture
def tplocation2() -> TPLocation:
    return TPLocation(id=2, name="WeCare Germering")


tplocation1copy = tplocation1


@pytest.fixture
def tpcourt1(tplocation1: TPLocation) -> TPCourt:
    return TPCourt(id=1, name="C01", location=tplocation1)


@pytest.fixture
def tpcourt2(tplocation2: TPLocation) -> TPCourt:
    return TPCourt(id=2, name="C07", location=tplocation2)


tpcourt1copy = tpcourt1


@pytest.fixture
def court1(tpcourt1: TPCourt) -> Court:
    return Court.from_tp_model(tpcourt1)


@pytest.fixture
def court2(tpcourt2: TPCourt) -> Court:
    return Court.from_tp_model(tpcourt2)


court1copy = court1


type TPPlayerMatchFactoryType = Callable[..., TPPlayerMatch]


@pytest.fixture
def TPPlayerMatchFactory(tpdraw1: TPDraw) -> TPPlayerMatchFactoryType:
    def playermatch_maker(**kwargs: Any) -> TPPlayerMatch:
        defaults = {
            "id": kwargs.get("planning", 1),
            "draw": tpdraw1,
        }
        return TPPlayerMatch(**defaults | kwargs)

    return playermatch_maker


type TPPlayerFactoryType = Callable[..., TPPlayerMatch]


@pytest.fixture
def TPPlayerFactory(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpentry1: TPEntry
) -> TPPlayerFactoryType:
    def player_maker(**kwargs: Any) -> TPPlayerMatch:
        defaults = {"id": kwargs.get("planning", 1), "entry": tpentry1}
        enforced = {"van1": None, "van2": None, "matchnr": None}
        return TPPlayerMatchFactory(**defaults | kwargs | enforced)

    return player_maker


@pytest.fixture
def pmplayer1(TPPlayerFactory: TPPlayerFactoryType, tpentry1: TPEntry) -> TPPlayerMatch:
    return TPPlayerFactory(id=1, planning=4001, wn=3001, vn=3005, entry=tpentry1)


@pytest.fixture
def pmplayer2(TPPlayerFactory: TPPlayerFactoryType, tpentry2: TPEntry) -> TPPlayerMatch:
    return TPPlayerFactory(id=2, planning=4002, wn=3001, vn=3005, entry=tpentry2)


pmplayer1copy = pmplayer1


@pytest.fixture
def pmbye(TPPlayerFactory: TPPlayerFactoryType) -> TPPlayerMatch:
    return TPPlayerFactory(planning=4008, entry=None)


@pytest.fixture
def pm1(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType, tpentry1: TPEntry, tpcourt1: TPCourt
) -> TPPlayerMatch:
    return TPPlayerMatchFactory(
        id=141,
        matchnr=14,
        entry=tpentry1,
        planning=3001,
        van1=4001,
        van2=4002,
        wn=2001,
        vn=2003,
        court=tpcourt1,
        time=datetime(2025, 6, 1, 11, 30),
    )


@pytest.fixture
def pm2(
    TPPlayerMatchFactory: TPPlayerMatchFactoryType,
    tpentry1: TPEntry,
) -> TPPlayerMatch:
    return TPPlayerMatchFactory(
        id=421,
        matchnr=42,
        entry=tpentry1,
        planning=2001,
        van1=3001,
        van2=3002,
        wn=1001,
        vn=1002,
    )


pm1copy = pm1


type TPMatchFactoryType = Callable[..., TPMatch]


@pytest.fixture
def TPMatchFactory() -> TPMatchFactoryType:
    def match_maker(
        pm: TPPlayerMatch,
        tpentry2: TPEntry | None,
        lldiff: int,
        pldiff: int | None = None,
        iddiff: int = 1,
    ) -> TPMatch:
        if pm.entry is not None and tpentry2 is not None:
            entry = tpentry2.model_copy(update={"event": pm.entry.event})
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
        return TPMatch(pm1=pm, pm2=pm2)

    return match_maker


@pytest.fixture
def tpmatch1(
    TPMatchFactory: TPMatchFactoryType,
    pm1: TPPlayerMatch,
    tpentry2: TPEntry,
) -> TPMatch:
    return TPMatchFactory(pm1, tpentry2, lldiff=4)


tpmatch1copy = tpmatch1


@pytest.fixture
def tpmatch2(
    TPMatchFactory: TPMatchFactoryType,
    pm2: TPPlayerMatch,
    tpentry2: TPEntry,
) -> TPMatch:
    return TPMatchFactory(pm2, tpentry2, lldiff=2)


@pytest.fixture
def match1(tpmatch1: TPMatch) -> Match:
    return Match.from_tpmatch(tpmatch1)


@pytest.fixture
def match2(tpmatch2: TPMatch) -> Match:
    return Match.from_tpmatch(tpmatch2)


match1copy = match1


@pytest.fixture
def tpmatch_pending(
    TPMatchFactory: TPMatchFactoryType,
    pm2: TPPlayerMatch,
) -> TPMatch:
    return TPMatchFactory(pm2, None, lldiff=2)


@pytest.fixture
def match_pending(tpmatch_pending: TPMatch) -> Match:
    return Match.from_tpmatch(tpmatch_pending)


@pytest.fixture
def tournament1(
    match1: Match,
    match2: Match,
    entry1: Entry,
    entry2: Entry,
    entry12: Entry,
    entry21: Entry,
    court1: Court,
    court2: Court,
    draw1: Draw,
    draw2: Draw,
) -> Tournament:
    t = Tournament(
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
def tournament2(match1: Match, entry1: Entry, entry2: Entry) -> Tournament:
    t = Tournament(name="Test 2")
    t.add_match(match1)
    t.add_entry(entry1)
    t.add_entry(entry2)
    return t


tournament1copy = tournament1
