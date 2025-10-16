from dataclasses import replace

import pytest

from tptools.entry import Country
from tptools.namepolicy import CountryNamePolicy
from tptools.namepolicy.policybase import RegexpSubstTuple


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


def test_code_instead_of_name_warns_when_titlecase(
    policy: CountryNamePolicy, country1: Country, caplog: pytest.LogCaptureFixture
) -> None:
    policy = replace(policy, use_country_code=True, titlecase=True)
    _ = policy(country1)
    assert caplog.messages[0].startswith("Ignoring CountryNamePolicy")


def test_code_instead_of_name_warns_when_regexp(
    policy: CountryNamePolicy, country1: Country, caplog: pytest.LogCaptureFixture
) -> None:
    policy = replace(policy, use_country_code=True, regexps=[RegexpSubstTuple("", "")])
    _ = policy(country1)
    assert caplog.messages[0].startswith("Ignoring CountryNamePolicy")


def test_code_instead_no_warns(
    policy: CountryNamePolicy, country1: Country, caplog: pytest.LogCaptureFixture
) -> None:
    policy = replace(policy, use_country_code=True, regexps=None, titlecase=False)
    _ = policy(country1)
    assert not caplog.messages
