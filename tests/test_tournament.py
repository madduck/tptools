from .fixtures import *  # noqa: F403, F401


def test_tournament_matches_pending(demo_tournament):
    matches = list(demo_tournament.get_matches())
    assert len(matches) == 8


def test_tournament_matches_with_played(demo_tournament):
    matches = list(demo_tournament.get_matches(include_played=True))
    assert len(matches) == 8


def test_tournament_matches_with_not_ready(demo_tournament):
    matches = list(demo_tournament.get_matches(include_not_ready=True))
    assert len(matches) == 21


def test_tournament_entries(demo_tournament):
    entries = list(demo_tournament.get_entries())
    assert len(entries) == 23


def test_tournament_no_court_means_empty(demo_tournament):
    for match in demo_tournament.get_matches(include_not_ready=True):
        if not match.court:
            assert match.court is None
