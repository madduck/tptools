import pytest

from tptools.drawtype import DrawType
from tptools.models import Club, Country, Draw, Event, Stage


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
