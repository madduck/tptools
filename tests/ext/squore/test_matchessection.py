import pytest

from tptools.export import Match
from tptools.ext.squore import MatchesSection

from .conftest import MatchesSectionFactoryType


@pytest.fixture
def ms1(
    MatchesSectionFactory: MatchesSectionFactoryType, sqmatch1: Match
) -> MatchesSection:
    return MatchesSectionFactory(name="ms1", matches=[sqmatch1])


def test_repr(ms1: MatchesSection) -> None:
    assert repr(ms1) == "MatchesSection(name='ms1', nmatches=1, expanded=False)"


def test_str(ms1: MatchesSection) -> None:
    assert str(ms1) == "\xa0ms1"


def test_matches_section_expanded(
    MatchesSectionFactory: MatchesSectionFactoryType,
) -> None:
    ms = MatchesSectionFactory(expanded=True)
    assert str(ms).startswith("+")


def test_matches_section_prefix_default(ms1: MatchesSection) -> None:
    assert str(ms1).startswith("\xa0")


def test_matches_section_dump(
    MatchesSectionFactory: MatchesSectionFactoryType, sqmatch1: Match
) -> None:
    ms = MatchesSectionFactory(name="section name", matches=(sqmatch1,))
    dump = ms.model_dump()
    assert dump["name"].endswith("section name")
    assert len(dump["matches"]) == 1
