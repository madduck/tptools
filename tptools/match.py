import enum

from tptools.logger import get_logger
from tptools.playermatch import PlayerMatch, SourcePlayerMatch
from tptools.entry import Entry

logger = get_logger(__name__)


class Match:

    class Status(enum.Enum):
        INVALID = -99
        DUPLICATE = -98
        BYE = -2
        PLAYER = -1
        UNKNOWN = 0
        UNPLAYED = 1
        SCHEDULED = 2
        READY = 3
        PLAYED = 4
        SKIPPED = 5
        BYED = 6

        def is_match(self):
            return self.value > self.UNKNOWN.value

        def is_scheduled(self):
            return self.value >= self.SCHEDULED.value

        def is_ready(self):
            return self.value == self.READY.value

        def is_played(self):
            return self.value >= self.PLAYED.value

    def __init__(
        self, playermatch, *, match_getter, entry_getter=None, court_xform=None
    ):
        self._playermatch = PlayerMatch(playermatch)
        self._match_getter = match_getter
        self._entry_getter = entry_getter
        if callable(court_xform):
            self._court_xform = court_xform
        else:
            self._court_xform = lambda identity: identity
        if self._playermatch.status == PlayerMatch.Status.MATCH:

            planning = self._playermatch["planning"]

            def get_playermatch(index):
                source = match_getter(playermatch[f"van{index}"])
                if not source.get("entry"):
                    if planning == source["wn"]:
                        return SourcePlayerMatch(
                            source, SourcePlayerMatch.Role.WINNER
                        )
                    elif planning == source["vn"]:
                        return SourcePlayerMatch(
                            source, SourcePlayerMatch.Role.LOSER
                        )
                return PlayerMatch(source)

            self._sources = [get_playermatch(s) for s in (1, 2)]
        else:
            self._sources = (None, None)
        self._entries = [None, None]

    event = property(lambda s: s._playermatch.get_event())
    draw = property(lambda s: s._playermatch.get_draw())
    id = property(lambda s: s._playermatch.id)
    time = property(lambda s: s._playermatch.get_time())
    court = property(lambda s: s._court_xform(s._playermatch.get_court()))
    status = property(lambda s: Match.get_match_status(s))

    def json(self, *, modmap=None):
        basemap = {
            "time": lambda t: t.isoformat(),
            "status": lambda s: (s.value, s.name.lower()),
        }

        def get_entryfields(e):
            fields = {
                "name": lambda e: Entry.make_team_name(e.players),
                "short": lambda e: Entry.make_team_name(e.playersshort),
                "club": lambda e: Entry.make_team_name(e.clubs),
                "country": lambda e: Entry.make_team_name(e.countries),
            }
            return {k: l(e) for k, l in fields.items()}

        basemap |= {f"player{i}": get_entryfields for i in (1, 2)}

        if modmap is not None:
            modmap = basemap | modmap
        else:
            modmap = basemap

        ret = {}
        for prop in [
            p
            for p in dir(self.__class__)
            if isinstance(getattr(self.__class__, p), property)
        ]:
            value = getattr(self, prop)
            if prop in modmap:
                value = modmap[prop](value)
            ret[prop] = value

        return ret


    def as_dict(self):
        return dict(
            matchid=self.id,
            date=self.time.strftime("%F") if self.time else None,
            time=self.time.strftime("%H:%M %:z") if self.time else None,
            court=self.court,
            player1=str(self.player1),
            player2=str(self.player2),
            event=self.event,
            draw=self.draw,
            status=self.status.name,
        )

    @classmethod
    def get_match_status(klass, match):
        if match._playermatch.status == PlayerMatch.Status.PLAYER:
            return klass.Status.PLAYER

        elif match._playermatch.status == PlayerMatch.Status.BYE:
            return klass.Status.BYE

        elif match._playermatch.status == PlayerMatch.Status.DUPLICATE:
            return klass.Status.DUPLICATE

        elif match._playermatch.status != PlayerMatch.Status.MATCH:
            return klass.Status.INVALID

        elif (
            match._sources[0].status == PlayerMatch.Status.BYE
            or match._sources[1].status == PlayerMatch.Status.BYE
        ):
            return klass.Status.BYED

        elif match._playermatch.get("winner", 0) > 0:
            return klass.Status.PLAYED

        elif match._playermatch.get_time():
            if (
                match._sources[0].status == PlayerMatch.Status.PENDING
                or match._sources[1].status == PlayerMatch.Status.PENDING
            ):
                return klass.Status.SCHEDULED
            else:
                return klass.Status.READY

        elif (
            match._playermatch.get("team1set1", 0) == 0
            and match._playermatch.get("team2set1", 0) == 0
        ):
            return klass.Status.UNPLAYED

        return klass.Status.UNKNOWN

    def is_match(self):
        return self.status.is_match()

    def is_played(self):
        return self.status.is_played()

    def is_scheduled(self):
        return self.status.is_scheduled()

    def is_ready(self):
        return self.status.is_ready()

    def __str__(self):
        if self.is_match():
            return (
                f"<Match[{self._playermatch.id}] "
                f"{self.status.name} "
                f"{self.player1}—{self.player2}"
                ">"
            )
        elif self.status == self.Status.BYE:
            return "<BYE>"
        elif self.status == self.Status.PLAYER:
            return f"<Entry[{self._entry}]>"

        return (
            f"<Match[{self._playermatch.id}] {self.status} "
            f"{self._playermatch}>"
        )

    __repr__ = __str__

    def _get_player(self, index, *, entry_getter=None):
        entry_getter = entry_getter or self._entry_getter
        if not self._entries[index] and entry_getter:
            self._entries[index] = self._sources[index].get_entry(
                entry_getter=entry_getter
            )

        if self._entries[index]:
            return self._entries[index]

        else:
            return self._sources[index]

    player1 = property(lambda s: s._get_player(0))
    player2 = property(lambda s: s._get_player(1))
