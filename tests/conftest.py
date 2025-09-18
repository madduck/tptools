import pytest

from tptools.models import Event


@pytest.fixture
def event1() -> Event:
    return Event(id=1, name="Herren 1", abbreviation="H1", gender=2)


@pytest.fixture
def event2() -> Event:
    return Event(id=2, name="Damen 1", abbreviation="D1", gender=1)


event1copy = event1
