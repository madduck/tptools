from collections.abc import Callable

import pytest

from tptools.drawtype import DrawType
from tptools.models import Club, Country, Draw, Entry, Event, Player, Stage
from tptools.slot import Bye, Playceholder, Slot, Unknown


@pytest.fixture
def event1() -> Event:
    return Event(id=1, name="Herren 1", abbreviation="H1", gender=2)


@pytest.fixture
def event2() -> Event:
    return Event(id=2, name="Damen 1", abbreviation="D1", gender=1)


event1copy = event1


@pytest.fixture
def stage1(event1: Event) -> Stage:
    return Stage(id=1, name="Qual", event=event1)


@pytest.fixture
def stage2(event2: Event) -> Stage:
    return Stage(id=2, name="Main", event=event2)


stage1copy = stage1


@pytest.fixture
def draw1(stage1: Stage) -> Draw:
    return Draw(id=1, name="Baum", type=DrawType.MONRAD, size=8, stage=stage1)


@pytest.fixture
def draw2(stage2: Stage) -> Draw:
    return Draw(id=2, name="Gruppe", type=DrawType.GROUP, size=3, stage=stage2)


draw1copy = draw1


@pytest.fixture
def club1() -> Club:
    return Club(id=1, name="RSC")


@pytest.fixture
def club2() -> Club:
    return Club(id=2, name="SomeClub")


club1copy = club1


@pytest.fixture
def country1() -> Country:
    return Country(id=1, name="Holland", code="NL")


@pytest.fixture
def country2() -> Country:
    return Country(id=2, name="Deutschland")


country1copy = country1


@pytest.fixture
def player1(club1: Club, country2: Country) -> Player:
    return Player(
        id=1, firstname="Martin", lastname="Krafft", club=club1, country=country2
    )


@pytest.fixture
def player2(club2: Club, country1: Country) -> Player:
    return Player(
        id=2, firstname="Iddo", lastname="Hoeve", club=club2, country=country1
    )


player1copy = player1


@pytest.fixture
def entry1(event1: Event, player1: Player) -> Entry:
    return Entry(id=1, event=event1, player1=player1)


@pytest.fixture
def entry2(event2: Event, player2: Player) -> Entry:
    return Entry(id=2, event=event2, player1=player2)


entry1copy = entry1


type EntryFactoryType = Callable[[int, Event, str], Entry]


@pytest.fixture
def EntryFactory() -> EntryFactoryType:
    def entry_maker(id: int, event: Event, name: str) -> Entry:
        p = Player(id=id, lastname="", firstname=name)
        return Entry(p, event=event)

    return entry_maker


@pytest.fixture
def entry12(event1: Event, player1: Player, player2: Player) -> Entry:
    return Entry(id=1, event=event1, player1=player1, player2=player2)


@pytest.fixture
def entry21(event2: Event, player1: Player, player2: Player) -> Entry:
    return Entry(id=2, event=event2, player1=player2, player2=player1)


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
def slot1(entry1: Entry) -> Slot:
    return Slot(content=entry1)


@pytest.fixture
def slot2(entry2: Entry) -> Slot:
    return Slot(content=entry2)


@pytest.fixture
def slot21(entry21: Entry) -> Slot:
    return Slot(content=entry21)


@pytest.fixture
def slot12(entry12: Entry) -> Slot:
    return Slot(content=entry12)
