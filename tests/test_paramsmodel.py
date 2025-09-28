import pytest

from tptools.namepolicy import PairCombinePolicyParams, PlayerNamePolicyParams


class CombinedParams(PairCombinePolicyParams, PlayerNamePolicyParams): ...


@pytest.fixture
def combined_params() -> CombinedParams:
    return CombinedParams()


def test_extract_subset(combined_params: CombinedParams) -> None:
    pcp = PairCombinePolicyParams.extract_subset(combined_params)
    assert pcp == dict(PairCombinePolicyParams())


def test_make_from_superset(combined_params: CombinedParams) -> None:
    pcp = PairCombinePolicyParams.make_from_parameter_superset(combined_params)
    assert pcp == PairCombinePolicyParams()
