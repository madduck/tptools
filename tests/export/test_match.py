from tptools.export.match import Match, MatchStruct


def test_repr(expmatch1: Match) -> None:
    assert repr(expmatch1) == (
        "Match(tpmatch=TPMatch(id='1-14', draw.name='Baum', matchnr=14, "
        "time=datetime(2025, 6, 1, 11, 30), court='Sports4You, C01', "
        "slot1.name='Martin Krafft', slot2.name='Iddo Hoeve', "
        "planning=3001/5, van=4001/2, wnvn=2001/3,2005/7, status=ready))"
    )


def test_str(expmatch1: Match) -> None:
    assert str(expmatch1) == "1-14 [Baum] [4001/2 → 3001/5 → 2001/3,2005/7] (ready)"


def test_model_dump(expmatch1: Match) -> None:
    match = expmatch1.model_dump()
    assert set(match.keys()) == set(MatchStruct.__annotations__.keys())
    assert match["A"] == expmatch1.tpmatch.slot1.id
    assert match["B"] == expmatch1.tpmatch.slot2.id
