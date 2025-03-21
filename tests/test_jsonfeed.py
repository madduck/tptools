from tptools.jsonfeed import JSONFeedMaker

from .fixtures import *  # noqa: F403, F401


def test_jsonfeed_maker():
    jfm = JSONFeedMaker(a="b", c="d", matches=[])
    data = jfm.get_data()
    assert data["config"]["a"] == "b"
    assert "Matches" in data
    assert len(data["Matches"]) == 0


def test_jsonfeed_maker_name():
    jfm = JSONFeedMaker(name="test", matches=[])
    data = jfm.get_data()
    assert data["name"] == "test"


def test_jsonfeed_maker_with_matches(demo_tournament):
    jfm = JSONFeedMaker(a="b", c="d", matches=demo_tournament.get_matches())
    data = jfm.get_data()
    assert len(data["Matches"]) == 8
