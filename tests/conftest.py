import pytest

from tptools.models import Event, Stage


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
