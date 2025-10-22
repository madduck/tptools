from collections.abc import Callable
from typing import Literal

import pytest
from pytest_mock import MockerFixture

from tptools.entry import Club, Country, Player
from tptools.ext.squore import SquoreEntry
from tptools.sqlmodels import TPEntry, TPPlayer


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
    assert sqentry.model_dump()[field] == exp  # pyright: ignore[reportTypedDictNotRequiredAccess]


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
    assert sqentrydbl.model_dump()[field] == exp  # pyright: ignore[reportTypedDictNotRequiredAccess]


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
        sqentry.model_dump(context={policyname: namepolicy})[field]  # pyright: ignore[reportTypedDictNotRequiredAccess]
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
        sqentrydbl.model_dump(  # pyright: ignore[reportTypedDictNotRequiredAccess]
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


@pytest.mark.parametrize("field", ["club", "country"])
def test_none_field_omits_from_struct(
    tpplayer1: TPPlayer, tpentry1: TPEntry, field: str
) -> None:
    player1 = tpplayer1.model_copy(update={field: None})
    entry1 = tpentry1.model_copy(update={"player1": player1})
    sqentry = SquoreEntry.from_tp_model(entry1)
    assert field not in sqentry.model_dump()
