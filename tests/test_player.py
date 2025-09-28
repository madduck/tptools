from collections.abc import Mapping

import pytest

from tptools.sqlmodels import TPPlayer


def test_club_has_id(tpplayer1: TPPlayer) -> None:
    assert tpplayer1.clubid_


def test_country_has_id(tpplayer1: TPPlayer) -> None:
    assert tpplayer1.countryid_


def test_repr(tpplayer1: TPPlayer) -> None:
    assert repr(tpplayer1) == (
        "TPPlayer(id=1, lastname='Krafft', firstname='Martin', "
        "country.name='Deutschland', club.name='RSC')"
    )


def test_str(tpplayer1: TPPlayer) -> None:
    assert str(tpplayer1) == "Martin Krafft (RSC, Deutschland)"


def test_eq(tpplayer1: TPPlayer, tpplayer1copy: TPPlayer) -> None:
    assert tpplayer1 == tpplayer1copy


def test_ne(tpplayer1: TPPlayer, tpplayer2: TPPlayer) -> None:
    assert tpplayer1 != tpplayer2


def test_lt(tpplayer1: TPPlayer, tpplayer2: TPPlayer) -> None:
    assert tpplayer2 < tpplayer1


def test_le(tpplayer1: TPPlayer, tpplayer2: TPPlayer, tpplayer1copy: TPPlayer) -> None:
    assert tpplayer2 <= tpplayer1 and tpplayer1 <= tpplayer1copy


def test_gt(tpplayer1: TPPlayer, tpplayer2: TPPlayer) -> None:
    assert tpplayer1 > tpplayer2


def test_ge(tpplayer1: TPPlayer, tpplayer2: TPPlayer, tpplayer1copy: TPPlayer) -> None:
    assert tpplayer1 >= tpplayer2 and tpplayer1 >= tpplayer1copy


def test_no_cmp(tpplayer1: TPPlayer) -> None:
    with pytest.raises(NotImplementedError):
        assert tpplayer1 == object()


def test_cmp_without_club(tpplayer1: TPPlayer) -> None:
    tpplayer2 = tpplayer1.model_copy(update={"club": None})
    assert tpplayer1 < tpplayer2


def test_cmp_without_country(tpplayer1: TPPlayer) -> None:
    tpplayer2 = tpplayer1.model_copy(update={"country": None})
    assert tpplayer1 < tpplayer2


def test_constructor_with_empty_lastname() -> None:
    assert TPPlayer(id=1, lastname="", firstname="test").name == "test"


def test_constructor_with_empty_firstname() -> None:
    assert TPPlayer(id=1, lastname="test", firstname="").name == "test"


@pytest.mark.parametrize("rel", ["club", "country"])
def test_model_dump_has_related_models(tpplayer1: TPPlayer, rel: str) -> None:
    md = tpplayer1.model_dump()
    assert f"{rel}id_" not in md
    assert isinstance(md.get(rel), Mapping)
