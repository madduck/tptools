from typing import TypedDict

from pydantic import ConfigDict, TypeAdapter


class PerMatchOverridableConfig(TypedDict, total=False):
    useHandInHandOutScoring: bool
    numberOfPointsToWinGame: int
    numberOfGamesToWinMatch: int
    tieBreakFormat: str
    timerPauseBetweenGames: int
    skipMatchSettings: bool

    __pydantic_config__ = ConfigDict(extra="forbid")  # type: ignore[misc]


PerMatchConfigValidator = TypeAdapter(PerMatchOverridableConfig)


class Config(PerMatchOverridableConfig, total=False):
    shareAction: str
    PostResult: str
    LiveScoreUrl: str
    captionForPostMatchResultToSite: str
    autoSuggestToPostResult: bool
    postDataPreference: str
    hideCompletedMatchesFromFeed: bool
    locationLast: str
    turnOnLiveScoringForMatchesFromFeed: bool
    postEveryChangeToSupportLiveScore: bool
    Placeholder_Match: str


ConfigValidator = TypeAdapter(Config)
