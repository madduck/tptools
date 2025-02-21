from tptools.entry import Entry
from tptools.draw import Draw


class Tournament:
    def __init__(self, *, entries=None, playermatches=None, court_xform=None):
        self._draws = {}
        if entries:
            self.read_entries(entries)
        else:
            self._entries = None
            self._entry_getter = None

        if playermatches:
            self.read_playermatches(
                playermatches, entry_getter=self._entry_getter
            )

        self._court_xform = court_xform

    def __str__(self):
        return (
            f"<Tournament entries={len(self._entries or [])}"
            " draws={len(self._draws)}>"
        )

    __repr__ = __str__

    def read_entries(self, entries):
        self._entries = {r["entryid"]: Entry(r) for r in entries}
        self._entry_getter = self._entries.get

    def read_playermatches(self, playermatches, *, entry_getter=None):
        matches_by_draws = {}
        for playermatch in playermatches:
            matches_by_draws.setdefault(playermatch["draw"], []).append(
                playermatch
            )

        for drawid, matches in matches_by_draws.items():
            if not (draw := self._draws.get(drawid)):
                draw = Draw(
                    event=matches[0]["eventname"], draw=matches[0]["drawname"]
                )
                self._draws[drawid] = draw

            draw.read_playermatches(
                matches, entry_getter=entry_getter or self._entry_getter
            )

    def get_matches(
        self,
        *,
        include_played=False,
        include_not_ready=False,
        entry_getter=None,
    ):
        for draw in self._draws.values():
            yield from draw.get_matches(
                include_played=include_played,
                include_not_ready=include_not_ready,
                entry_getter=entry_getter or self._entry_getter,
            )

    def get_entries(self):
        yield from self._entries.values()

    def get_match(self, matchid, *, entry_getter=None):
        for draw in self._draws.values():
            for match in draw.get_matches(
                include_played=True,
                include_not_ready=True,
                entry_getter=entry_getter or self._entry_getter,
            ):
                if match.id == matchid:
                    return match

    def get_entry(self, entryid):
        if self._entries:
            return self._entries.get(entryid)
