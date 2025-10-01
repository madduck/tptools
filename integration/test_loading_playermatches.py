import pytest
import pytest_subtests
from sqlalchemy import ScalarResult

from tptools.sqlmodels import TPPlayerMatch

PLAYERMATCH_ID_BY_STATUS = {
    TPPlayerMatch.Status.PLAYER: [  # {{{
        1221,
        1223,
        1224,
        1225,
        1226,
        1227,
        1228,
        1527,
        1528,
        1529,
        1530,
        1531,
        1532,
        1533,
        1534,
        1535,
        1536,
        1537,
        1538,
        1539,
        1540,
        1541,
        1542,
        1563,
        1564,
        1565,
        1572,
        1573,
        1574,
        1582,
        1583,
        1590,
        1591,
        1592,
        1602,
        1603,
        1604,
        1609,
        1610,
        1611,
        1616,
        1617,
        1619,
    ],  # }}}
    TPPlayerMatch.Status.BYE: [  # {{{
        1222,
        1581,
        1605,
        1612,
        1618,
    ],  # }}}
    TPPlayerMatch.Status.NOTPLAYED: [  # {{{
        1211,
        1217,
        1485,
        1486,
        1501,
        1584,
        1585,
        1586,
        1588,
        1632,
        1634,
    ],  # }}}
    TPPlayerMatch.Status.PLAYED: [  # {{{
        1199,
        1200,
        1205,
        1206,
        1207,
        1208,
        1209,
        1213,
        1214,
        1215,
        1216,
        1218,
        1219,
        1220,
        1483,
        1484,
        1495,
        1496,
        1497,
        1498,
        1499,
        1500,
        1502,
        1504,
        1508,
        1511,
        1512,
        1513,
        1514,
        1515,
        1516,
        1517,
        1518,
        1519,
        1520,
        1521,
        1522,
        1523,
        1524,
        1525,
        1526,
        1566,
        1567,
        1568,
        1569,
        1570,
        1571,
        1576,
        1578,
        1579,
        1580,
        1587,
        1589,
        1593,
        1594,
        1595,
        1596,
        1597,
        1598,
        1600,
        1613,
        1614,
        1615,
        1623,
        1630,
        1631,
        1633,
    ],  # }}}
    TPPlayerMatch.Status.PENDING: [  # {{{
        1469,  # two byes leading in
        1470,  # two byes leading in
        1465,
        1466,
        1201,
        1202,
        1203,
        1204,
        1463,
        1464,
        1471,
        1472,
        1473,
        1474,
        1475,
        1476,
        1477,
        1478,
        1487,
        1488,
        1489,
        1490,
        1491,
        1492,
        1493,
        1494,
        1599,
        1601,
        1606,
        1608,
        1620,
        1621,
        1622,
        1624,
        1625,
        1626,
        1627,
        1629,
        # the following are all "ready" in the sense that the two
        # opponents are known, but there is no way to find that
        # out from just the PlayerMatch
        1197,
        1198,
        1210,
        1212,
        1467,
        1468,
        1479,
        1481,
        1480,  # no time/court assigned
        1482,  # no time/court assigned
        1503,
        1507,
        1505,
        1509,
        1506,
        1510,
        1575,
        1577,
        1607,
        1628,
    ],  # }}}
}


@pytest.fixture
def status_by_id() -> dict[int, TPPlayerMatch.Status]:
    status_by_id: dict[int, TPPlayerMatch.Status] = {}
    for status, playermatches in PLAYERMATCH_ID_BY_STATUS.items():
        status_by_id |= dict.fromkeys(playermatches, status)
    return status_by_id


def test_loading_playermatches(all_tpplayermatches: list[TPPlayerMatch]) -> None:
    assert len(all_tpplayermatches) == 184


def test_status(
    all_tpplayermatches: ScalarResult[TPPlayerMatch],
    status_by_id: dict[int, TPPlayerMatch.Status],
    subtests: pytest_subtests.SubTests,
) -> None:
    n = 0
    for pm in all_tpplayermatches:
        n += 1
        with subtests.test(_=pm):
            assert pm.status == (expected := status_by_id[pm.id]), (
                f"{pm!r} not at expected status: {expected}"
            )
    assert n == 184


# vim:fdm=marker:fdl=0
