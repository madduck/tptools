import pytest
from pydantic import ValidationError

from tptools.ext.squore.config import ConfigValidator, PerMatchConfigValidator


def test_config_invalid_key() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        _ = ConfigValidator.validate_python({"invalidKey": True})


@pytest.mark.parametrize(
    "keyname",
    [
        "iNvAlIdKeY",
        "shareAction",
        "PostResult",
        "LiveScoreUrl",
        "captionForPostMatchResultToSite",
        "autoSuggestToPostResult",
        "hideCompletedMatchesFromFeed",
        "postDataPreference",
        "locationLast",
        "turnOnLiveScoringForMatchesFromFeed",
        "postEveryChangeToSupportLiveScore",
        "Placeholder_Match",
    ],
)
def test_per_match_config_invalid_key(keyname: str) -> None:
    with pytest.raises(ValidationError, match=f"\n{keyname}\n.*extra_forbidden"):
        _ = PerMatchConfigValidator.validate_python({keyname: True})
