import pytest
from sqlmodel import Session, select

from tptools.models import Setting

type SettingsDict = dict[str, str | None]


@pytest.fixture
def all_settings(db_session: Session) -> SettingsDict:
    ret = {}
    for setting in db_session.exec(select(Setting)):
        ret[setting.name] = setting.value
    return ret


def test_loading_settings(all_settings: SettingsDict) -> None:
    assert len(all_settings) == 159


def test_tournament_name(all_settings: SettingsDict) -> None:
    assert all_settings["Tournament"] == "27. RSC Memorial Turnier 2025"
