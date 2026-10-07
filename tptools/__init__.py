from .court import Court, CourtSelectionParams
from .devcourtmap import DeviceCourtMap
from .draw import Draw, Event, Stage
from .drawtype import DrawType
from .entry import Entry, Player
from .match import Match
from .tournament import MatchSelectionParams, Tournament, load_tournament
from .tpmatch import TPMatchStatus as MatchStatus
from .util import ScoresType

VERSION: str | None
try:
    from ._version import version as VERSION

except ImportError:  # pragma: nocover
    VERSION = None

__all__ = [
    "Court",
    "CourtSelectionParams",
    "DeviceCourtMap",
    "Draw",
    "DrawType",
    "Entry",
    "Event",
    "load_tournament",
    "Match",
    "MatchStatus",
    "MatchSelectionParams",
    "Player",
    "ScoresType",
    "Stage",
    "Tournament",
    "VERSION",
]
