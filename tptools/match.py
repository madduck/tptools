import logging
from datetime import datetime
from functools import partial
from typing import Any, Callable, Literal, Self, cast

from pydantic import BaseModel, model_validator

from .matchstatus import MatchStatus
from .mixins import ComparableMixin, ReprMixin, StrMixin
from .slot import Slot, Unknown
from .sqlmodels import Court, Draw, Entry, PlayerMatch
from .util import normalise_time, reduce_common_prefix, zero_to_none

logger = logging.getLogger(__name__)


class Match(ReprMixin, StrMixin, ComparableMixin, BaseModel):
    pm1: PlayerMatch
    pm2: PlayerMatch

    _slots: tuple[Slot, Slot] | None = None

    def set_slots(self, slot1: Slot, slot2: Slot) -> None:
        self._slots = (slot1, slot2)

    def _check_winner_consistency(self) -> Self:
        if (a := zero_to_none(self.pm1.winner)) is not None and (
            b := zero_to_none(self.pm2.winner)
        ) is not None:
            assert a + b == 3, f"winner fields: {a}+{b} != 3 "

        else:
            b = zero_to_none(self.pm2.winner)
            assert a is None and b is None, f"winner fields inconsistent: {a} vs. {b}"
        return self

    def _check_event_consistency(self) -> Self:
        if self.pm1.entry is not None and self.pm2.entry is not None:
            assert self.pm1.entry.event == self.pm2.entry.event, (
                "match between players in different events"
            )
        return self

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        try:
            assert self.pm1.status.is_match, "got a player"
            assert self.pm2.status.is_match, "got a player"

            # It seems that PlayerMatch pairs always have the winner first, i.e. with
            # the lower planning number, so let's ensure that:
            if self.pm1.planning > self.pm2.planning:
                self.pm1, self.pm2 = self.pm2, self.pm1

            assert None not in self.pm2.van, "Missing van pointer"

            assert self.pm1.van == self.pm2.van, "Inconsistent van pointers"

            for field, acceptable in {
                "id": (None,),
                "entry": (None,),
                "wn": (None, 0),
                "vn": (None, 0),
            }.items():
                a = getattr(self.pm1, field)
                b = getattr(self.pm2, field)
                assert (a in acceptable and b in acceptable and a == b) or a != b, (
                    f"same value for '{field}'"
                )

            for field in (
                "matchnr",
                "draw",
                "court",
                "time",
            ):
                # these fields must be identical between the two playermatches
                # lest the 2nd match's field be None:
                b = getattr(self.pm2, field)
                if b is None:
                    continue
                a = getattr(self.pm1, field)
                if (
                    massager := cast(
                        Callable[[Any], Any], self.__massage_fields__.get(field)
                    )
                ) is not None:
                    a = massager(a)
                    b = massager(b)
                assert a == b, f"different values for '{field}': {a} vs. {b}"

            self._check_winner_consistency()
            self._check_event_consistency()

        except AssertionError as err:
            raise AssertionError(f"Validating {self!r}: {err}") from err

        else:
            return self

    @property
    def id(self) -> str:
        return f"{self.draw.id}-{self.matchnr}"

    @property
    def matchnr(self) -> int:
        return self.pm1.matchnr

    @property
    def draw(self) -> Draw:
        return self.pm1.draw

    @property
    def court(self) -> Court | None:
        return self.pm1.court

    @property
    def time(self) -> datetime | None:
        return self.pm1.time

    @property
    def played(self) -> bool:
        winner = zero_to_none(self.pm1.winner)
        return winner is not None

    @property
    def winner(self) -> Entry | None:
        return self.pm1.entry if self.played else None

    @property
    def van(self) -> tuple[int, int]:
        # Safe to cast since consistency checks above already ensured that
        # van pointers aren't None for Match
        return cast(tuple[int, int], self.pm1.van)

    @property
    def is_group_match(self) -> bool:
        return self.pm1.reversehomeaway or self.pm2.reversehomeaway

    def _slot(self, idx: Literal[0] | Literal[1]) -> Slot:
        if self._slots is None:
            pm = getattr(self, f"pm{idx + 1}")
            return Slot(content=pm.entry or Unknown())

        return self._slots[idx]

    @property
    def slot1(self) -> Slot:
        return self._slot(0)

    @property
    def slot2(self) -> Slot:
        return self._slot(1)

    @property
    def is_ready(self) -> bool:
        return self.slot1.is_ready and self.slot2.is_ready

    @property
    def status(self) -> MatchStatus:
        ret = MatchStatus.from_playermatch_status_pair(self.pm1.status, self.pm2.status)
        logger.debug(f"Status {ret} deduced from {self.pm1!r} and {self.pm2!r}")
        if ret == MatchStatus.PENDING:
            if self.is_ready:
                logger.debug("Overriding status for match that is ready")
                return MatchStatus.READY
            elif self.is_group_match:
                logger.debug("Overriding status for group match")
                return MatchStatus.READY

        return ret

    def _time_repr(self) -> str:
        return repr(self.time).replace("datetime.", "")

    def _van_repr(self) -> str | None:
        return self.pm1._van_repr()

    def _wnvn_repr(self) -> str:
        return ",".join(
            (pm._ll_repr("wn", "vn") or "None" for pm in (self.pm1, self.pm2))
        )

    def _court_repr(self) -> str | None:
        return str(self.court) if self.court else None

    def _planning_repr(self) -> str | None:
        return reduce_common_prefix(
            str(self.pm1.planning) if self.pm1.planning is not None else None,
            str(self.pm2.planning) if self.pm2.planning is not None else None,
        )

    def _pm_eq_sort(self) -> tuple[PlayerMatch, PlayerMatch]:
        ret = sorted((self.pm1, self.pm2))
        return ret[0], ret[1]

    def _status_repr(self) -> str:
        return self.status.name.lower()

    __eq_fields__ = (_pm_eq_sort,)
    __str_template__ = (
        "{self.id} [{self.draw.name}] "
        "[{self._van_repr()} → {self._planning_repr()} → {self._wnvn_repr()}] "
        "({self.status})"
    )
    __repr_fields__ = (
        "id",
        "draw.name",
        "matchnr",
        ("time", _time_repr, False),
        ("court", _court_repr, True),
        "slot1?.name",
        "slot2?.name",
        ("planning", _planning_repr, False),
        ("van", _van_repr, False),
        ("wnvn", _wnvn_repr, False),
        ("status", _status_repr, False),
        "winner?.name",
    )

    __massage_fields__ = {
        "van1": zero_to_none,
        "van2": zero_to_none,
        "winner": zero_to_none,
        "time": partial(normalise_time, nodate_value=datetime(1899, 12, 30)),
    }
