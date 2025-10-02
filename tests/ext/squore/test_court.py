from pytest_mock import MockerFixture

from tptools.ext.squore import SquoreCourt


def test_namepolicy_default(sqcourt: SquoreCourt) -> None:
    assert sqcourt.model_dump() == str(sqcourt)


def test_namepolicy(
    sqcourt: SquoreCourt,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="courtnamepolicy")
    policy.return_value = "court"
    assert sqcourt.model_dump(context={"courtnamepolicy": policy}) == "court"
    policy.assert_called_once_with(sqcourt)
