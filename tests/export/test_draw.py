from tptools.export.draw import Draw, DrawStruct


def test_repr(expdraw1: Draw) -> None:
    assert repr(expdraw1) == (
        "Draw(tpdraw=TPDraw(id=1, name='Baum', stage.name='Qual', type=MONRAD, size=8))"
    )


def test_str(expdraw1: Draw) -> None:
    assert str(expdraw1) == "Baum, Qual, Herren 1"


def test_model_dump(expdraw1: Draw) -> None:
    draw = expdraw1.model_dump()
    assert draw.keys() == DrawStruct.__annotations__.keys()
