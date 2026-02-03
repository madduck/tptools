from io import BytesIO

import pytest

from tptools.court import Court
from tptools.devcourtmap import DeviceCourtMap


@pytest.fixture
def courts(court1: Court, court2: Court) -> dict[str, Court]:
    return {
        "court1": court1.model_copy(update={"name": "C1"}),
        "court2": court2,
        "court10": Court(id=10, name="C10"),
        "court11": Court(id=11, name="C11"),
        "invalid": Court(id=99, name="invalid"),
    }


@pytest.fixture
def tomldevmap(courts: dict[str, Court]) -> BytesIO:
    devmap: dict[str, str | int] = {f"192.0.2.{c.id}": c.name for c in courts.values()}
    devmap["192.0.2.11"] = 11  # courts can be identified by ID as well as name
    toml = "\n".join([f"{ip} = {court!r}" for ip, court in devmap.items()])
    return BytesIO(toml.encode())


def test_toml_reader(tomldevmap: BytesIO) -> None:
    devmap = DeviceCourtMap.read_toml_devmap(tomldevmap)
    assert "192.0.2.1" in devmap
    assert devmap["192.0.2.2"] == "C07"


@pytest.mark.parametrize(
    "input, exp",
    [
        ("C1", (None, 1)),
        ("2-C1", (2, 1)),
        ("-3-C4", (3, 4)),
        ("C01", (None, 1)),
        ("C42", (None, 42)),
        ("c2", (None, 2)),
        ("court3", (None, 3)),
        ("Court4", (None, 4)),
        ("COURT5", (None, 5)),
        ("Court 6", (None, 6)),
        ("Court 08", (None, 8)),
        ("C 7", None),
        ("Cou7", None),
    ],
)
def test_name_normaliser(input: str, exp: tuple[int | None, int] | None) -> None:
    assert DeviceCourtMap.normalise_court_name_for_matching(input) == exp


@pytest.fixture
def devcourtmap(tomldevmap: BytesIO) -> DeviceCourtMap:
    return DeviceCourtMap(tomldevmap)


@pytest.mark.parametrize(
    "ip, text", [("192.0.2.1", "C1"), ("192.0.2.2", "C07"), ("192.0.2.3", None)]
)
def test_find_match(devcourtmap: DeviceCourtMap, ip: str, text: str | None) -> None:
    assert devcourtmap.find_match_for_ip(ip) == text


@pytest.mark.parametrize(
    "ip, court",
    [("192.0.2.1", "court1"), ("192.0.2.2", "court2"), ("192.0.2.3", "court3")],
)
def test_find_court(
    devcourtmap: DeviceCourtMap, ip: str, court: str, courts: dict[str, Court]
) -> None:
    assert devcourtmap.find_court_for_ip(ip, courts.values()) == courts.get(court)


def test_find_court_as_int(
    devcourtmap: DeviceCourtMap, courts: dict[str, Court]
) -> None:
    assert devcourtmap.find_court_for_ip("192.0.2.11", courts.values()) == courts.get(
        "court11"
    )


def test_find_without_any_courts(devcourtmap: DeviceCourtMap) -> None:
    assert devcourtmap.find_court_for_ip("192.0.2.11") is None


def test_find_abnormal_court_name(
    devcourtmap: DeviceCourtMap, courts: dict[str, Court]
) -> None:
    assert devcourtmap.find_court_for_ip("192.0.2.99", courts.values()) is None
