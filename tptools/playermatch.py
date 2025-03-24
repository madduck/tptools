import enum
import datetime
from dateutil.parser import parse as date_parser

from tptools.logger import get_logger

logger = get_logger(__name__)


class PlayerMatch(dict):

    class Status(enum.Enum):
        BYE = -3
        PLAYER = -2
        PENDING = -1
        MATCH = 0

    def __init__(self, other):
        super().__init__(other)
        self._entry = self.get("entry")
        if self.get("van1") in (0, None):
            assert self.get("van2") in (0, None)
            assert self.get("winner", 0) == 0
            if self._entry:
                logger.debug(f"Found player (entry={self._entry})")
                self._status = self.Status.PLAYER
            else:
                logger.debug("Found Bye")
                self._status = self.Status.BYE
        else:
            logger.debug("Found match")
            self._status = self.Status.MATCH

    id = property(lambda s: s.get("matchid", -1))
    status = property(lambda s: s._status)

    def __str__(self):
        if self._status == self.Status.BYE:
            return "BYE"
        elif self._status == self.Status.PLAYER:
            return f"E{self._entry}"
        else:
            return f"M{self.id}"

    def __repr__(self):
        return "<" f"{self.__class__.__name__} " f"{self.id} ({self.status.name})" ">"

    def get_entry(self, *, entry_getter):
        return entry_getter(self._entry)

    def get_time(self):
        if plan := self.get("plandate"):
            try:
                dt = date_parser(plan).replace(
                    tzinfo=datetime.datetime.now().astimezone().tzinfo
                )
            except TypeError:
                dt = plan

            return dt if dt.date() > datetime.date(1900, 1, 1) else None

    def get_event(self):
        return self.get("eventname")

    def get_draw(self):
        return self.get("drawname")

    def get_location(self):
        return self.get("locationname")

    def get_court(self):
        if not (cname := self.get("courtname")):
            return None
        ret = str(cname)
        if loc := self.get("locationname"):
            ret = f"{loc} - {ret}"
        return ret


class SourcePlayerMatch(PlayerMatch):

    class Role(enum.Enum):
        UNKNOWN = "Unknown"
        WINNER = "Winner"
        LOSER = "Loser"

    def __init__(self, other, role):
        super().__init__(other)
        self._role = role
        if self._status == PlayerMatch.Status.MATCH:
            self._status = PlayerMatch.Status.PENDING

    role = property(lambda s: s._role)

    def __str__(self):
        return f"{self.role.value[0]}{self.id}"

    players = property(lambda s: (s._role,))
    playersshort = property(lambda s: (str(s),))
    clubs = property(lambda s: ("?",))
    countries = property(lambda s: ("?",))
