import json
from collections.abc import Mapping

from tptools.entry import Entry

PLACEHOLDER_MATCH=(
    "${date} ${time} : "
    "${FirstOfList:~${A}~${A.name}~} [${A.country}] [${A.club}] - "
    "${FirstOfList:~${B}~${B.name}~} [${B.country}] [${B.club}] : "
    "${result}"
)

class JSONFeedMaker:

    def __init__(
        self,
        *,
        matches,
        name=None,
        court_xform=None,
        useHandInHandOutScoring=False,
        tiebreakFormat="TwoClearPoints",
        numberOfPointsToWinGame=11,
        numberOfGamesToWinMatch=3,
        skipMatchSettings=True,
        hideCompletedMatchesFromFeed=True,
        shareAction="PostResult",
        PostResult=None,
        captionForPostMatchResultToSite="Send result to tournament control",
        autoSuggestToPostResult=True,
        postDataPreference="JsonDetailsOnly",
        timerPauseBetweenGames=90,
        turnOnLiveScoringForMatchesFromFeed=True,
        postEveryChangeToSupportLiveScore=True,
        Placeholder_Match=PLACEHOLDER_MATCH,
        **config
    ):
        # https://squore.double-yellow.be/demo/demo.matches.json
        self._name = name

        known = dict(
            useHandInHandOutScoring=useHandInHandOutScoring,
            tiebreakFormat=tiebreakFormat,
            numberOfPointsToWinGame=numberOfPointsToWinGame,
            numberOfGamesToWinMatch=numberOfGamesToWinMatch,
            skipMatchSettings=skipMatchSettings,
            hideCompletedMatchesFromFeed=hideCompletedMatchesFromFeed,
            PostResult=PostResult,
            captionForPostMatchResultToSite=captionForPostMatchResultToSite,  # noqa:E501
            shareAction=shareAction,
            autoSuggestToPostResult=autoSuggestToPostResult,
            postDataPreference=postDataPreference,
            timerPauseBetweenGames=timerPauseBetweenGames,
            turnOnLiveScoringForMatchesFromFeed=turnOnLiveScoringForMatchesFromFeed,  # noqa:E501
            postEveryChangeToSupportLiveScore=postEveryChangeToSupportLiveScore,  # noqa:E501
            Placeholder_Match=Placeholder_Match,
        )

        self._config = config | {k: v for k, v in known.items() if v}

        if not isinstance(matches, Mapping):
            matches = {"Matches": matches}

        self._matches = {}
        for sect, matches in matches.items():
            if sect == "config":
                raise ValueError("Section name for matches cannot be 'config'")
            self._matches[sect] = [
                JSONFeedMaker.match_to_dict(m, court_xform=court_xform)
                for m in matches
            ]

    @classmethod
    def match_to_dict(klass, match, *, court_xform=None):
        ret = {
            "id": match.id,
            "court": (
                court_xform(match.court)
                if callable(court_xform)
                else match.court
            ),
            "A": {
                "name": Entry.make_team_name(match.player1.playersshort),
                "club": Entry.make_team_name(match.player1.clubs, joinstr="/"),
                "country": Entry.make_team_name(
                    match.player1.countries, joinstr="/"
                ),
            },
            "B": {
                "name": Entry.make_team_name(match.player2.playersshort),
                "club": Entry.make_team_name(match.player2.clubs, joinstr="/"),
                "country": Entry.make_team_name(
                    match.player2.countries, joinstr="/"
                ),
            }
        }

        if match.time:
            ret["date"] = match.time.strftime("%a %F")
            ret["time"] = match.time.strftime("%H:%M")

        if match.event == match.draw:
            ret["field"] = match.event
        else:
            ret["field"] = f'{match.event}, {match.draw}'

        return ret

    def get_data(self):
        ret = {
            "config": self._config,
        }
        if self._name:
            ret['name'] = self._name
        return ret | self._matches

    def get_json(self):
        return json.dumps(self.get_data())
