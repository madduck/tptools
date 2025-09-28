from pytest_mock import MockerFixture

from tptools.export import Court
from tptools.sqlmodels import TPCourt


def test_repr(expcourt1: Court) -> None:
    assert repr(expcourt1) == (
        "Court(tpcourt=TPCourt(id=1, name='C01', location.name='Sports4You'))"
    )


def test_str(expcourt1: Court) -> None:
    assert str(expcourt1) == "Sports4You, C01"


def test_courtnamepolicy_default(expcourt1: Court) -> None:
    assert (
        expcourt1.model_dump() == expcourt1.tpcourt.name if expcourt1.tpcourt else None
    )


def test_courtnamepolicy_invocation(expcourt1: Court, mocker: MockerFixture) -> None:
    policy = mocker.stub(name="courtnamepolicy")
    policy.return_value = "court"
    assert expcourt1.model_dump(context={"courtnamepolicy": policy}) == "court"
    policy.assert_called_once_with(expcourt1.tpcourt)


def test_court_id_passthrough(tpcourt1: TPCourt) -> None:
    assert Court(tpcourt=tpcourt1).id == tpcourt1.id


def test_court_name_passthrough(tpcourt1: TPCourt) -> None:
    assert Court(tpcourt=tpcourt1).name == tpcourt1.name


def test_court_location_passthrough(tpcourt1: TPCourt) -> None:
    assert Court(tpcourt=tpcourt1).location == tpcourt1.location


def test_cmp_eq(expcourt1: Court, expcourt1copy: Court) -> None:
    assert expcourt1 == expcourt1copy


def test_cmp_ne(expcourt1: Court, expcourt2: Court) -> None:
    assert expcourt1 != expcourt2


def test_cmp_lt(expcourt1: Court, expcourt2: Court) -> None:
    assert expcourt1 < expcourt2


def test_cmp_le(expcourt1: Court, expcourt1copy: Court, expcourt2: Court) -> None:
    assert expcourt1 < expcourt2 and expcourt1 <= expcourt1copy


def test_cmp_gt(expcourt1: Court, expcourt2: Court) -> None:
    assert expcourt2 > expcourt1


def test_cmp_ge(expcourt1: Court, expcourt1copy: Court, expcourt2: Court) -> None:
    assert expcourt2 > expcourt1 and expcourt1 >= expcourt1copy
