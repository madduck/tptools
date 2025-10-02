from collections.abc import Callable
from typing import Literal

import pytest
from pytest_mock import MockerFixture

from tptools.entry import Club, Country, Player
from tptools.ext.squore import SquoreEntry


@pytest.mark.parametrize(
    "field, exp",
    [
        ("name", "Martin Krafft"),
        ("club", "RSC"),
        ("country", "Deutschland"),
    ],
)
def test_namepolicy_default(
    sqentry: SquoreEntry,
    field: Literal["name"] | Literal["club"] | Literal["country"],
    exp: str,
) -> None:
    assert sqentry.model_dump()[field] == exp


@pytest.mark.parametrize(
    "field, exp",
    [
        ("name", "Martin Krafft&Iddo Hoeve"),
        ("club", "RSC&SomeClub"),
        ("country", "Deutschland&Holland"),
    ],
)
def test_doubles_namepolicy_default(
    sqentrydbl: SquoreEntry,
    field: Literal["name"] | Literal["club"] | Literal["country"],
    exp: str,
) -> None:
    assert sqentrydbl.model_dump()[field] == exp


@pytest.mark.parametrize(
    "field, policyname, argfn",
    [
        ("name", "playernamepolicy", lambda e: e.player1),
        ("club", "clubnamepolicy", lambda e: e.player1.club),
        ("country", "countrynamepolicy", lambda e: e.player1.country),
    ],
)
def test_namepolicy_application(
    sqentry: SquoreEntry,
    mocker: MockerFixture,
    field: Literal["name"] | Literal["club"] | Literal["country"],
    policyname: str,
    argfn: Callable[[SquoreEntry], Player | Club | Country],
) -> None:
    namepolicy = mocker.stub(name="namepolicy")
    namepolicy.return_value = "namepolicy"
    assert (
        sqentry.model_dump(context={policyname: namepolicy})[field]
        == namepolicy.return_value
    )
    namepolicy.assert_called_once_with(argfn(sqentry))


@pytest.mark.parametrize(
    "field, policyname, firstnone, argfn",
    [
        ("name", "playernamepolicy", False, lambda n, e: getattr(e, f"player{n}")),
        ("club", "clubnamepolicy", True, lambda n, e: getattr(e, f"player{n}").club),
        (
            "country",
            "countrynamepolicy",
            True,
            lambda n, e: getattr(e, f"player{n}").country,
        ),
    ],
)
def test_doubles_namepolicy_application(
    sqentrydbl: SquoreEntry,
    mocker: MockerFixture,
    field: Literal["name"] | Literal["club"] | Literal["country"],
    policyname: str,
    argfn: Callable[[int, SquoreEntry], Player | Club | Country],
    firstnone: bool,
) -> None:
    namepolicy = mocker.stub(name="namepolicy")
    namepolicy.return_value = "namepolicy"
    paircombinepolicy = mocker.stub(name="paircombinepolicy")
    paircombinepolicy.return_value = "combined"
    assert (
        sqentrydbl.model_dump(
            context={
                policyname: namepolicy,
                "paircombinepolicy": paircombinepolicy,
            }
        )[field]
        == paircombinepolicy.return_value
    )
    namepolicy.assert_any_call(argfn(1, sqentrydbl))
    namepolicy.assert_any_call(argfn(2, sqentrydbl))
    paircombinepolicy.assert_any_call(
        namepolicy.return_value, namepolicy.return_value, first_can_be_none=firstnone
    )


def test_no_name_discernable(mocker: MockerFixture, sqentry: SquoreEntry) -> None:
    namepolicy = mocker.stub(name="namepolicy")
    namepolicy.return_value = None
    with pytest.raises(ValueError, match="No player name discernable"):
        _ = sqentry.model_dump(context={"playernamepolicy": namepolicy})
