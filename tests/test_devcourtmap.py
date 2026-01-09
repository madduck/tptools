from io import BytesIO

import pytest

from tptools.court import Court
from tptools.devcourtmap import DeviceCourtMap


@pytest.fixture
def tomldevmap() -> BytesIO:
    devmap = {
        "192.0.2.1": "C1",
        "192.0.2.2": "C07",
    }
    toml = "\n".join([f'{ip} = "{court}"' for ip, court in devmap.items()])
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
    devcourtmap: DeviceCourtMap, ip: str, court: str, court1: Court, court2: Court
) -> None:
    cm = {"court1": court1, "court2": court2}
    assert devcourtmap.find_court_for_ip(ip, cm.values()) == cm.get(court)
