from pytest_mock import MockerFixture

from tptools.export import Court


def test_repr(sqcourt1: Court) -> None:
    assert repr(sqcourt1) == (
        "Court(tpcourt=Court(id=1, name='C01', location.name='Sports4You'))"
    )


def test_str(sqcourt1: Court) -> None:
    assert str(sqcourt1) == "Sports4You, C01"


def test_courtnamepolicy_default(sqcourt1: Court) -> None:
    assert sqcourt1.model_dump() == sqcourt1.tpcourt.name if sqcourt1.tpcourt else None


def test_courtnamepolicy_invocation(sqcourt1: Court, mocker: MockerFixture) -> None:
    policy = mocker.stub(name="courtnamepolicy")
    policy.return_value = "court"
    assert sqcourt1.model_dump(context={"courtnamepolicy": policy}) == "court"
    policy.assert_called_once_with(sqcourt1.tpcourt)
