import pytest
from pydantic import ValidationError

from tptools.export import Tournament
from tptools.ext.squore import SquoreMatch, SquoreMatchStruct
from tptools.tpmatch import TPMatch


def test_repr(sqmatch1: SquoreMatch) -> None:
    assert repr(sqmatch1) == (
        "SquoreMatch(tpmatch=TPMatch(id='1-14', draw.name='Baum', matchnr=14, "
        "time=datetime(2025, 6, 1, 11, 30), court='Sports4You, C01', "
        "slot1.name='Martin Krafft', slot2.name='Iddo Hoeve', "
        "planning=3001/5, van=4001/2, wnvn=2001/3,2005/7, status=ready), nconfig=0)"
    )


def test_str(sqmatch1: SquoreMatch) -> None:
    assert str(sqmatch1) == "1-14 [Baum] [4001/2 → 3001/5 → 2001/3,2005/7] (ready)"


def test_model_dump(sqmatch1: SquoreMatch) -> None:
    match = sqmatch1.model_dump()
    assert set(match.keys()) < set(SquoreMatchStruct.__annotations__.keys())


def test_match_constructor_with_config_value(tpmatch1: TPMatch) -> None:
    match = SquoreMatch(tpmatch=tpmatch1, config={"numberOfPointsToWinGame": 11})
    data = match.model_dump()
    assert data.get("numberOfPointsToWinGame") == 11


def test_match_constructor_invalid_config_value(tpmatch1: TPMatch) -> None:
    with pytest.raises(ValidationError, match="should be a valid integer"):
        _ = SquoreMatch(tpmatch=tpmatch1, config={"numberOfPointsToWinGame": "eleven"})  # type: ignore[typeddict-item]


def test_match_constructor_invalid_config_key(tpmatch1: TPMatch) -> None:
    with pytest.raises(ValidationError, match="type=extra_forbidden"):
        _ = SquoreMatch(tpmatch=tpmatch1, config={"invalidKey": True})  # type: ignore[typeddict-unknown-key]


def test_match_resolve_entries_from_context(
    sqmatch1: SquoreMatch, exptournament1: Tournament
) -> None:
    sqmatch1.model_dump(context={"tournament": exptournament1})
