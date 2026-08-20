from typing import Literal, TypedDict

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


class EmulatorConfig(TypedDict, total=False):
    LikelihoodPlayerAWinsRallyInGame: list[int]
    LikelihoodPlayersMakeAppeal: list[int]
    LikelihoodUndoRequiredByRef: int
    LikelihoodSwitchServeSideOnHandout: int
    RallyDuration_Average: int
    RallyDuration_Deviation: int
    SpeedUpFactor: int


EmulatorConfigValidator = TypeAdapter(EmulatorConfig)


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
    emulate_Config: EmulatorConfig
    emulate_StartOnMatchSelection: bool
    emulate_AutoLoadNextMatch: (
        Literal["None"]
        | Literal["First"]
        | Literal["Next"]
        | Literal["NextLoopBackToFirstAfterLast"]
        | Literal["Last"]
    )


ConfigValidator = TypeAdapter(Config)
