from tptools.export import Draw, DrawStruct


def test_repr(sqdraw1: Draw) -> None:
    assert repr(sqdraw1) == (
        "Draw(tpdraw=Draw(id=1, name='Baum', stage.name='Qual', type=MONRAD, size=8))"
    )


def test_str(sqdraw1: Draw) -> None:
    assert str(sqdraw1) == "Baum, Qual, Herren 1"


def test_model_dump(sqdraw1: Draw) -> None:
    draw = sqdraw1.model_dump()
    assert draw.keys() == DrawStruct.__annotations__.keys()
