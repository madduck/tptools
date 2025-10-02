from pytest_mock import MockerFixture

from tptools.ext.squore import SquoreDraw


def test_namepolicy_default(sqdraw: SquoreDraw) -> None:
    dump = sqdraw.model_dump()
    assert isinstance(dump, dict)
    assert dump["name"] == sqdraw.name
    assert "stage" in dump
    assert "event" in dump


def test_namepolicy(
    sqdraw: SquoreDraw,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="drawnamepolicy")
    policy.return_value = "draw"
    assert sqdraw.model_dump(context={"drawnamepolicy": policy}) == "draw"
    policy.assert_called_once_with(sqdraw)
