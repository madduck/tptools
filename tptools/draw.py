from tptools.playermatch import PlayerMatch
from tptools.match import Match
from tptools.logger import get_logger

logger = get_logger(__name__)


class Draw:
    def __init__(
        self, *, event=None, draw=None, entry_getter=None, court_xform=None
    ):
        self._playermatches = {}
        self._name = draw
        if event and event != draw:
            self._name = f"{event}, {draw}"
        self._entry_getter = entry_getter
        self._court_xform = court_xform

    name = property(lambda s: s._name)

    def get_records_by_status(self, status):
        return {
            k: v for k, v in self._playermatches.items() if v.status == status
        }

    players = property(
        lambda s: s.get_records_by_status(PlayerMatch.Status.PLAYER)
    )
    byes = property(lambda s: s.get_records_by_status(PlayerMatch.Status.BYE))
    matches = property(
        lambda s: s.get_records_by_status(PlayerMatch.Status.MATCH)
    )

    def __str__(self):
        ret = "<Draw "
        if self._name:
            ret = f'{ret}"{self._name}" '
        return (
            f"{ret}players={len(self.players)} byes={len(self.byes)} "
            f"matches={len(self.matches)}>"
        )

    __repr__ = __str__

    def _add_playermatch(self, match, entry_getter):
        self._playermatches[match["planning"]] = match

    def read_playermatches(self, playermatches, *, entry_getter=None):
        for playermatch in playermatches:
            if playermatch.get("reversehomeaway"):
                continue
            self._add_playermatch(
                playermatch, entry_getter or self._entry_getter
            )

    def get_matches(
        self,
        *,
        include_played=False,
        include_not_ready=False,
        entry_getter=None,
        court_xform=None,
    ):
        for planning, pm in self.matches.items():
            m = Match(
                pm,
                entry_getter=entry_getter or self._entry_getter,
                match_getter=self._playermatches.get,
                court_xform=court_xform or self._court_xform,
            )
            if m.is_played() and not include_played:
                continue

            if not m.is_ready() and not include_not_ready:
                continue

            yield m
