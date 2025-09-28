from collections.abc import Mapping

import pytest

from tptools.sqlmodels import TPPlayer


def test_club_has_id(player1: TPPlayer) -> None:
    assert player1.clubid_


def test_country_has_id(player1: TPPlayer) -> None:
    assert player1.countryid_


def test_repr(player1: TPPlayer) -> None:
    assert repr(player1) == (
        "TPPlayer(id=1, lastname='Krafft', firstname='Martin', "
        "country.name='Deutschland', club.name='RSC')"
    )


def test_str(player1: TPPlayer) -> None:
    assert str(player1) == "Martin Krafft (RSC, Deutschland)"


def test_eq(player1: TPPlayer, player1copy: TPPlayer) -> None:
    assert player1 == player1copy


def test_ne(player1: TPPlayer, player2: TPPlayer) -> None:
    assert player1 != player2


def test_lt(player1: TPPlayer, player2: TPPlayer) -> None:
    assert player2 < player1


def test_le(player1: TPPlayer, player2: TPPlayer, player1copy: TPPlayer) -> None:
    assert player2 <= player1 and player1 <= player1copy


def test_gt(player1: TPPlayer, player2: TPPlayer) -> None:
    assert player1 > player2


def test_ge(player1: TPPlayer, player2: TPPlayer, player1copy: TPPlayer) -> None:
    assert player1 >= player2 and player1 >= player1copy


def test_no_cmp(player1: TPPlayer) -> None:
    with pytest.raises(NotImplementedError):
        assert player1 == object()


def test_cmp_without_club(player1: TPPlayer) -> None:
    player2 = player1.model_copy(update={"club": None})
    assert player1 < player2


def test_cmp_without_country(player1: TPPlayer) -> None:
    player2 = player1.model_copy(update={"country": None})
    assert player1 < player2


def test_constructor_with_empty_lastname() -> None:
    assert TPPlayer(id=1, lastname="", firstname="test").name == "test"


def test_constructor_with_empty_firstname() -> None:
    assert TPPlayer(id=1, lastname="test", firstname="").name == "test"


@pytest.mark.parametrize("rel", ["club", "country"])
def test_model_dump_has_related_models(player1: TPPlayer, rel: str) -> None:
    md = player1.model_dump()
    assert f"{rel}id_" not in md
    assert isinstance(md.get(rel), Mapping)
