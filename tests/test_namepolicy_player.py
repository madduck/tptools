import dataclasses
from dataclasses import FrozenInstanceError

import pytest

from tptools.namepolicy import PlayerNamePolicy
from tptools.sqlmodels import TPPlayer

FNAME = "Martin"
LNAME = "Krafft"
NAME = f"{FNAME} {LNAME}"


@pytest.fixture
def policy() -> PlayerNamePolicy:
    return PlayerNamePolicy()


def test_constructor(policy: PlayerNamePolicy) -> None:
    _ = policy


def test_frozen(policy: PlayerNamePolicy) -> None:
    with pytest.raises(FrozenInstanceError):
        policy.namejoinstr = "#"  # type: ignore[misc]


def test_passthrough(policy: PlayerNamePolicy, player1: TPPlayer) -> None:
    assert policy(player1) == "Martin Krafft"


def test_none(policy: PlayerNamePolicy) -> None:
    assert policy(None) is None


@pytest.mark.parametrize(
    "fnamemaxlen,result",
    [
        (0, "Krafft"),
        (1, "M.Krafft"),
        (2, "Ma.Krafft"),
        (6, "Martin Krafft"),
        (7, "Martin Krafft"),
    ],
)
def test_shorten(
    policy: PlayerNamePolicy, player1: TPPlayer, fnamemaxlen: int, result: str
) -> None:
    policy = dataclasses.replace(policy, fnamemaxlen=fnamemaxlen)
    assert policy(player1) == result


def test_no_fname(policy: PlayerNamePolicy, player1: TPPlayer) -> None:
    player = player1.model_copy(update={"firstname": None})
    assert policy(player) == "Krafft"


def test_no_lname(policy: PlayerNamePolicy, player1: TPPlayer) -> None:
    player = player1.model_copy(update={"lastname": None})
    assert policy(player) == "Martin"


def test_no_lname_fnamemaxlen_ignored(
    policy: PlayerNamePolicy, player1: TPPlayer
) -> None:
    player = player1.model_copy(update={"lastname": None})
    policy = dataclasses.replace(policy, fnamemaxlen=1)
    assert policy(player) == "Martin"


@pytest.mark.parametrize("name", [None, ""])
def test_no_name_whatsoever(
    name: None | str, policy: PlayerNamePolicy, player1: TPPlayer
) -> None:
    player = player1.model_copy(update={"lastname": name, "firstname": name})
    with pytest.raises(ValueError, match="Need at least a first or a last name"):
        _ = policy(player)


def test_empty_lname(policy: PlayerNamePolicy, player1: TPPlayer) -> None:
    player = player1.model_copy(update={"lastname": ""})
    assert policy(player) == "Martin"


def test_empty_fname(policy: PlayerNamePolicy, player1: TPPlayer) -> None:
    player = player1.model_copy(update={"firstname": ""})
    assert policy(player) == "Krafft"


@pytest.mark.parametrize("namejoinstr", [" ", "+", "&", "."])
def test_joinstr(policy: PlayerNamePolicy, namejoinstr: str, player1: TPPlayer) -> None:
    policy = dataclasses.replace(policy, namejoinstr=namejoinstr)
    assert policy(player1) == f"Martin{namejoinstr}Krafft"


@pytest.mark.parametrize("abbrjoinstr", [" ", ".", ". "])
def test_abbrjoinstr(
    policy: PlayerNamePolicy, abbrjoinstr: str, player1: TPPlayer
) -> None:
    policy = dataclasses.replace(policy, fnamemaxlen=1, abbrjoinstr=abbrjoinstr)
    assert policy(player1) == f"M{abbrjoinstr}Krafft"


@pytest.mark.parametrize(
    "fnamemaxlen, expected", [(-1, "Krafft Martin"), (0, "Krafft"), (1, "Krafft M.")]
)
def test_lnamefirst(
    policy: PlayerNamePolicy, fnamemaxlen: int, expected: str, player1: TPPlayer
) -> None:
    policy = dataclasses.replace(policy, fnamemaxlen=fnamemaxlen, lnamefirst=True)
    assert policy(player1) == expected


@pytest.mark.parametrize(
    "include_club,include_country,exp",
    [
        (True, True, "RSC, Deutschland"),
        (False, True, "Deutschland"),
        (True, False, "RSC"),
    ],
)
def test_include_country_club(
    policy: PlayerNamePolicy,
    player1: TPPlayer,
    include_club: bool,
    include_country: bool,
    exp: str,
) -> None:
    policy = dataclasses.replace(
        policy, include_club=include_club, include_country=include_country
    )
    assert policy(player1) == f"Martin Krafft ({exp})"
