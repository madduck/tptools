from tptools import Match


def test_repr(match1: Match) -> None:
    assert repr(match1) == (
        "Match(id='1-14', matchnr=14, draw=Draw(id=1, name='Baum', "
        "stage.name='Qual', type=MONRAD, size=8), time=datetime(2025, 6, 1, 11, 30), "
        "court=Court(id=1, name='C01', location.name='Sports4You'), "
        "A=Entry(event.name='Herren 1', player1.name='Martin Krafft'), "
        "B=Entry(event.name='Herren 1', player1.name='Iddo Hoeve'), "
        "status=ready, starttime=None, endtime=None, winner=None, scores=-)"
    )


def test_str(match1: Match) -> None:
    assert str(match1) == "1-14 ready on C01 (Sports4You) @ 11:30"


def test_cmp_eq(match1: Match, match1copy: Match) -> None:
    assert match1 == match1copy


def test_cmp_ne(match1: Match, match2: Match) -> None:
    assert match1 != match2


def test_cmp_lt(match1: Match, match2: Match) -> None:
    assert match1 < match2


def test_cmp_le(match1: Match, match1copy: Match, match2: Match) -> None:
    assert match1 < match2 and match1 <= match1copy


def test_cmp_gt(match1: Match, match2: Match) -> None:
    assert match2 > match1


def test_cmp_ge(match1: Match, match1copy: Match, match2: Match) -> None:
    assert match2 > match1 and match1 >= match1copy
