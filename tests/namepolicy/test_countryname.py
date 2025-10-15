from dataclasses import replace

import pytest

from tptools.entry import Country
from tptools.namepolicy import CountryNamePolicy


@pytest.fixture
def policy() -> CountryNamePolicy:
    return CountryNamePolicy()


def test_constructor(policy: CountryNamePolicy) -> None:
    _ = policy


def test_passthrough(policy: CountryNamePolicy, country1: Country) -> None:
    assert policy(country1) == "Holland"


def test_no_country(policy: CountryNamePolicy) -> None:
    _ = policy(None)


def test_titlecase_default(policy: CountryNamePolicy, country1: Country) -> None:
    foobar = country1.model_copy(update={"name": "foo bar"})
    assert policy(foobar) == "Foo Bar"


def test_titlecase_disabled(policy: CountryNamePolicy, country1: Country) -> None:
    foobar = country1.model_copy(update={"name": "foo bar"})
    policy = replace(policy, titlecase=False)
    assert policy(foobar) == "foo bar"


def test_code_instead_of_name(policy: CountryNamePolicy, country1: Country) -> None:
    policy = replace(policy, use_country_code=True)
    assert policy(country1) == "NL"


def test_code_instead_of_name_uses_name_when_code_absent(
    policy: CountryNamePolicy, country2: Country
) -> None:
    policy = replace(policy, use_country_code=True)
    assert policy(country2) == "Deutschland"
