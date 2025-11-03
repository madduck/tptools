import pytest
import pytest_subtests
from sqlalchemy import ScalarResult

from tptools.sqlmodels import TPPlayerMatch
from tptools.util import ScoresType

PLAYERMATCH_ID_BY_STATUS: dict[TPPlayerMatch.Status, list[tuple[int, ScoresType]]] = {
    TPPlayerMatch.Status.PLAYER: [  # {{{
        (1221, []),
        (1223, []),
        (1224, []),
        (1225, []),
        (1226, []),
        (1227, []),
        (1228, []),
        (1527, []),
        (1528, []),
        (1529, []),
        (1530, []),
        (1531, []),
        (1532, []),
        (1533, []),
        (1534, []),
        (1535, []),
        (1536, []),
        (1537, []),
        (1538, []),
        (1539, []),
        (1540, []),
        (1541, []),
        (1542, []),
        (1563, []),
        (1564, []),
        (1565, []),
        (1572, []),
        (1573, []),
        (1574, []),
        (1582, []),
        (1583, []),
        (1590, []),
        (1591, []),
        (1592, []),
        (1602, []),
        (1603, []),
        (1604, []),
        (1609, []),
        (1610, []),
        (1611, []),
        (1616, []),
        (1617, []),
        (1619, []),
    ],  # }}}
    TPPlayerMatch.Status.BYE: [  # {{{
        (1222, []),
        (1581, []),
        (1605, []),
        (1612, []),
        (1618, []),
    ],  # }}}
    TPPlayerMatch.Status.NOTPLAYED: [  # {{{
        (1211, []),
        (1217, []),
        (1485, []),
        (1486, []),
        (1501, []),
        (1502, []),
        (1632, []),
        (1634, []),
    ],  # }}}
    TPPlayerMatch.Status.PLAYED: [  # {{{
        (1199, [(11, 4), (11, 7), (13, 11)]),
        (1200, [(4, 11), (7, 11), (11, 13)]),
        (1205, [(11, 4), (11, 5), (11, 6)]),
        (1206, [(3, 11), (4, 11), (5, 11)]),
        (1207, [(4, 11), (5, 11), (6, 11)]),
        (1208, [(11, 3), (11, 4), (11, 5)]),
        (1209, []),  # a bye
        (1213, []),  # a bye
        (1214, [(11, 3), (3, 11), (6, 11), (6, 11)]),
        (1215, [(2, 11), (5, 11), (4, 11)]),
        (1216, [(6, 11), (11, 4), (5, 11), (8, 11)]),
        (1218, [(3, 11), (11, 3), (11, 6), (11, 6)]),
        (1219, [(11, 2), (11, 5), (11, 4)]),
        (1220, [(11, 6), (4, 11), (11, 5), (11, 8)]),
        (1483, [(5, 11), (5, 11), (3, 6)]),
        (1484, []),  # a bye
        (1495, [(11, 4), (11, 5), (11, 6)]),
        (1496, [(3, 11), (4, 11), (5, 11)]),
        (1497, []),  # a bye
        (1498, [(3, 11), (11, 13), (1, 11)]),
        (1499, [(4, 11), (5, 11), (6, 11)]),
        (1500, [(11, 3), (11, 4), (11, 5)]),
        (1502, [(11, 3), (13, 11), (11, 1)]),
        (1504, [(4, 11), (3, 11), (9, 11)]),
        (1508, [(11, 4), (11, 3), (11, 9)]),
        (1511, [(3, 11), (4, 11), (5, 11)]),
        (1512, [(11, 5), (11, 4), (3, 11), (11, 4)]),
        (1513, [(10, 12), (11, 13), (4, 11)]),
        (1514, [(11, 5), (11, 4), (11, 7)]),
        (1515, [(4, 11), (11, 6), (5, 11), (11, 3), (9, 11)]),
        (1516, [(4, 11), (5, 11), (6, 11)]),
        (1517, [(12, 14), (12, 14), (12, 14)]),
        (1518, [(4, 11), (6, 11), (7, 11)]),
        (1519, [(11, 3), (11, 4), (11, 5)]),
        (1520, [(5, 11), (4, 11), (11, 3), (4, 11)]),
        (1521, [(12, 10), (13, 11), (11, 4)]),
        (1522, [(5, 11), (4, 11), (7, 11)]),
        (1523, [(11, 4), (6, 11), (11, 5), (3, 11), (11, 9)]),
        (1524, [(11, 4), (11, 5), (11, 6)]),
        (1525, [(14, 12), (14, 12), (14, 12)]),
        (1526, [(11, 4), (11, 6), (11, 7)]),
        (1566, [(3, 11), (4, 11), (1, 11)]),
        (1567, [(7, 11), (4, 11), (9, 11)]),
        (1568, [(11, 3), (11, 4), (11, 1)]),
        (1569, [(9, 11), (8, 11), (11, 7), (5, 11)]),
        (1570, [(11, 7), (11, 4), (11, 9)]),
        (1571, [(11, 9), (11, 8), (7, 11), (11, 5)]),
        (1576, [(2, 11), (4, 11), (3, 11)]),
        (1578, [(6, 11), (11, 9), (13, 11), (2, 11), (9, 11)]),
        (1579, [(11, 2), (11, 4), (11, 3)]),
        (1580, [(11, 6), (9, 11), (11, 13), (11, 2), (11, 9)]),
        (1587, [(11, 6), (4, 11), (5, 11), (9, 11)]),
        (1589, [(6, 11), (11, 4), (11, 5), (11, 9)]),
        (1593, [(11, 6), (11, 9), (11, 4)]),
        (1594, [(3, 11), (2, 11), (1, 11)]),
        (1595, [(6, 11), (9, 11), (4, 11)]),
        (1596, [(5, 11), (6, 11), (7, 11)]),
        (1597, [(11, 3), (11, 2), (11, 1)]),
        (1598, [(11, 5), (11, 6), (11, 7)]),
        (1600, [(7, 11), (11, 8), (11, 6), (4, 11), (11, 13)]),
        (1613, [(5, 11), (4, 11), (6, 11)]),
        (1614, [(11, 4), (11, 3), (11, 2)]),
        (1615, []),  # a bye
        (1623, [(11, 7), (8, 11), (6, 11), (11, 4), (13, 11)]),
        (1630, [(11, 5), (11, 4), (11, 6)]),
        (1631, []),  # a bye
        (1633, [(4, 11), (3, 11), (2, 11)]),
    ],  # }}}
    TPPlayerMatch.Status.PENDING: [  # {{{
        (1469, []),  # two byes leading in
        (1470, []),  # two byes leading in
        (1465, []),
        (1466, []),
        (1201, []),
        (1202, []),
        (1203, []),
        (1204, []),
        (1463, []),
        (1464, []),
        (1471, []),
        (1472, []),
        (1473, []),
        (1474, []),
        (1475, []),
        (1476, []),
        (1477, []),
        (1478, []),
        (1487, []),
        (1488, []),
        (1489, []),
        (1490, []),
        (1491, []),
        (1492, []),
        (1493, []),
        (1494, []),
        (1599, []),
        (1601, []),
        (1606, []),
        (1608, []),
        (1620, []),
        (1621, []),
        (1622, []),
        (1624, []),
        (1625, []),
        (1626, []),
        (1627, []),
        (1629, []),
        # the following are all "ready" in the sense that the two
        # opponents are known, but there is no way to find that
        # out from just the PlayerMatch
        (1197, []),
        (1198, []),
        (1210, []),
        (1212, []),
        (1467, []),
        (1468, []),
        (1479, []),
        (1481, []),
        (1480, []),  # no time/court assigned
        (1482, []),  # no time/court assigned
        (1503, []),
        (1507, []),
        (1505, []),
        (1509, []),
        (1506, []),
        (1510, []),
        (1575, []),
        (1577, []),
        (1607, []),
        (1628, []),
        (1584, []),  # a bye in a group draw, which cannot be identified
        (1585, []),  # a bye in a group draw, which cannot be identified
        (1586, []),  # a bye in a group draw, which cannot be identified
        (1588, []),  # a bye in a group draw, which cannot be identified
    ],  # }}}
}


@pytest.fixture
def status_by_id() -> dict[int, TPPlayerMatch.Status]:
    status_by_id: dict[int, TPPlayerMatch.Status] = {}
    for status, playermatches in PLAYERMATCH_ID_BY_STATUS.items():
        status_by_id |= dict.fromkeys([p[0] for p in playermatches], status)
    return status_by_id


@pytest.fixture
def scores_by_id() -> dict[int, ScoresType]:
    scores_by_id: dict[int, ScoresType] = {}
    for playermatches in PLAYERMATCH_ID_BY_STATUS.values():
        scores_by_id |= {p[0]: p[1] for p in playermatches}
    return scores_by_id


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


def test_scores(
    all_tpplayermatches: ScalarResult[TPPlayerMatch],
    scores_by_id: dict[int, ScoresType],
    subtests: pytest_subtests.SubTests,
) -> None:
    n = 0
    for pm in all_tpplayermatches:
        n += 1
        with subtests.test(_=pm):
            assert pm.scores == (expected := scores_by_id[pm.id]), (
                f"{pm!r} not with expected score: {expected}"
            )
    assert n == 184


# vim:fdm=marker:fdl=0
