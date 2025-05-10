import pytest_subtests
from sqlalchemy import ScalarResult

from tptools.models import Entry


def test_loading_entries(all_entries: list[Entry]) -> None:
    assert len(all_entries) == 36


def test_all_entries_are_singles_and_unique(
    all_entries: ScalarResult[Entry], subtests: pytest_subtests.SubTests
) -> None:
    entries_seen = set()
    players_seen = set()
    n = 0
    for entry in all_entries:
        with subtests.test(_=entry):
            assert entry.player1
            assert entry.player1.country
            assert entry.player2 is None

            assert entry.id not in entries_seen

            assert entry.player1.id not in players_seen

        entries_seen.add(entry.id)
        players_seen.add(entry.player1.id)
        n += 1

    assert n > 0
