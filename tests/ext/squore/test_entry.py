from pytest_mock import MockerFixture

from tptools.export import Entry, EntryStruct


def test_repr(sqplayer1: Entry) -> None:
    assert repr(sqplayer1) == (
        "Entry(tpentry="
        "TPEntry(id=1, event.name='Herren 1', player1.name='Martin Krafft')"
        ")"
    )


def test_str(sqplayer1: Entry) -> None:
    assert str(sqplayer1) == "Martin Krafft"


def test_model_dump(sqplayer1: Entry) -> None:
    player = sqplayer1.model_dump()
    assert player.keys() == EntryStruct.__annotations__.keys()


def test_playernamepolicy_invocation(
    sqplayer1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="playernamepolicy")
    policy.return_value = "Martin"
    assert (
        sqplayer1.model_dump(context={"playernamepolicy": policy})["name"] == "Martin"
    )
    policy.assert_called_once_with(sqplayer1.tpentry.player1)


def test_clubnamepolicy_invocation(
    sqplayer1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="clubnamepolicy")
    policy.return_value = "RSC"
    assert sqplayer1.model_dump(context={"clubnamepolicy": policy})["club"] == "RSC"
    policy.assert_called_once_with(sqplayer1.tpentry.player1.club)


def test_countrynamepolicy_invocation(
    sqplayer1: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="countrynamepolicy")
    policy.return_value = "Deutschland"
    assert (
        sqplayer1.model_dump(context={"countrynamepolicy": policy})["country"]
        == "Deutschland"
    )
    policy.assert_called_once_with(sqplayer1.tpentry.player1.country)


def test_paircombinepolicy_invocation(
    sqplayer12: Entry,
    mocker: MockerFixture,
) -> None:
    policy = mocker.stub(name="paircombinepolicy")
    policy.return_value = "Team"
    assert (
        sqplayer12.model_dump(context={"paircombinepolicy": policy})["name"] == "Team"
    )
