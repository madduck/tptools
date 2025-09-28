from pytest_mock import MockerFixture

from tptools.export import Entry, EntryStruct
from tptools.sqlmodels import Entry as TPEntry


def test_repr(expentry1: Entry) -> None:
    assert repr(expentry1) == (
        "Entry(tpentry="
        "Entry(id=1, event.name='Herren 1', player1.name='Martin Krafft')"
        ")"
    )


def test_str(expentry1: Entry) -> None:
    assert str(expentry1) == "Martin Krafft"


def test_entry_id_passthrough(entry1: TPEntry) -> None:
    assert Entry(tpentry=entry1).id == entry1.id


def test_entry_name_passthrough(entry1: TPEntry) -> None:
    assert Entry(tpentry=entry1).name == entry1.name


def test_cmp_eq(expentry1: Entry, expentry1copy: Entry) -> None:
    assert expentry1 == expentry1copy


def test_cmp_ne(expentry1: Entry, expentry2: Entry) -> None:
    assert expentry1 != expentry2


def test_cmp_lt(expentry1: Entry, expentry2: Entry) -> None:
    assert expentry2 < expentry1


def test_cmp_le(expentry1: Entry, expentry1copy: Entry, expentry2: Entry) -> None:
    assert expentry2 < expentry1 and expentry1 <= expentry1copy


def test_cmp_gt(expentry1: Entry, expentry2: Entry) -> None:
    assert expentry1 > expentry2


def test_cmp_ge(expentry1: Entry, expentry1copy: Entry, expentry2: Entry) -> None:
    assert expentry1 > expentry2 and expentry1 >= expentry1copy


def test_model_dump(expentry1: Entry) -> None:
    player = expentry1.model_dump()
    assert player.keys() == EntryStruct.__annotations__.keys()


def test_playernamepolicy_invocation(
    expentry1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="playernamepolicy")
    policy.return_value = "Martin"
    assert (
        expentry1.model_dump(context={"playernamepolicy": policy})["name"] == "Martin"
    )
    policy.assert_called_once_with(expentry1.tpentry.player1)


def test_clubnamepolicy_invocation(
    expentry1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="clubnamepolicy")
    policy.return_value = "RSC"
    assert expentry1.model_dump(context={"clubnamepolicy": policy})["club"] == "RSC"
    policy.assert_called_once_with(expentry1.tpentry.player1.club)


def test_countrynamepolicy_invocation(
    expentry1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="countrynamepolicy")
    policy.return_value = "Deutschland"
    assert (
        expentry1.model_dump(context={"countrynamepolicy": policy})["country"]
        == "Deutschland"
    )
    policy.assert_called_once_with(expentry1.tpentry.player1.country)


def test_paircombinepolicy_invocation(
    expentry12: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="paircombinepolicy")
    policy.return_value = "Team"
    assert (
        expentry12.model_dump(context={"paircombinepolicy": policy})["name"] == "Team"
    )
