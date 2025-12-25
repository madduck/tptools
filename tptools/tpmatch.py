from __future__ import annotations

import logging
from datetime import datetime
from enum import StrEnum, auto
from functools import partial
from typing import Any, Callable, Literal, Self, cast

import tzlocal
from pydantic import BaseModel, model_validator

from .mixins import ComparableMixin, ReprMixin, StrMixin
from .slot import Bye, Playceholder, Slot, Unknown
from .sqlmodels import TPCourt, TPDraw, TPEntry, TPPlayerMatch
from .util import (
    ScoresType,
    normalise_time,
    reduce_common_prefix,
    scores_to_string,
    zero_to_none,
)

logger = logging.getLogger(__name__)

LOCAL_TZ = tzlocal.get_localzone()


class TPMatchStatus(StrEnum):
    READY = auto()
    PENDING = TPPlayerMatch.Status.PENDING
    PLAYED = TPPlayerMatch.Status.PLAYED
    NOTPLAYED = TPPlayerMatch.Status.NOTPLAYED

    @classmethod
    def from_playermatch_status_pair(
        cls, a: TPPlayerMatch.Status, b: TPPlayerMatch.Status
    ) -> TPMatchStatus:
        if a.is_player or b.is_player:
            raise ValueError(
                "MatchStatus needs two PlayerMatchStatus that are not players or byes"
            )

        if a == b:
            return cls(a)

        elif TPPlayerMatch.Status.NOTPLAYED in (a, b):
            return cls.NOTPLAYED

        else:
            return cls.PENDING


class TPMatch(ComparableMixin, ReprMixin, StrMixin, BaseModel):
    pm1: TPPlayerMatch
    pm2: TPPlayerMatch

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

    def _check_score_consistency(self) -> Self:
        sc2 = self.pm2.get_scores(reversed=self.pm2.winner == 2)
        if (
            (self.pm1.scorestatus or 0) > 0
            and (self.pm2.scorestatus or 0) == 0
            and len(sc2) == 0
        ):
            return self
        assert (sc1 := self.pm1.get_scores(reversed=self.pm1.winner == 2)) == sc2, (
            f"PlayerMatches have different scorelines: {sc1} vs. {sc2}"
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
            self._check_score_consistency()

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
    def draw(self) -> TPDraw:
        return self.pm1.draw

    @property
    def court(self) -> TPCourt | None:
        return self.pm1.court

    @property
    def time(self) -> datetime | None:
        return (
            self.pm1.time.replace(tzinfo=LOCAL_TZ)
            if self.pm1.time is not None
            else None
        )

    @property
    def played(self) -> bool:
        winner = zero_to_none(self.pm1.winner)
        return winner is not None

    @property
    def winner(self) -> TPEntry | None:
        # TODO:this won't work for group draws, as TP doesn't fill entry for those
        return self.pm1.entry if self.played else None

    @property
    def won_by(self) -> Literal["A"] | Literal["B"] | None:
        match zero_to_none(self.pm1.winner):
            case 1:
                return "A"
            case 2:
                return "B"
            case _:
                return None

    @property
    def scores(self) -> ScoresType:
        return self.pm1.get_scores()

    @property
    def starttime(self) -> datetime | None:
        return (
            self.pm1.starttime.replace(tzinfo=LOCAL_TZ)
            if self.pm1.starttime is not None
            else None
        )

    @property
    def endtime(self) -> datetime | None:
        return (
            self.pm1.endtime.replace(tzinfo=LOCAL_TZ)
            if self.pm1.endtime is not None
            else None
        )

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
            # The winner of a match always corresponds to the first of the two
            # PlayerMatches, so we need to restore order of the slots if player B
            # won. This seems to be what the winner field encodes, i.e. if winner is 1,2
            # across the two PlayerMatches, then the first player (A) is the winner,
            # else B
            if (self.pm2.winner or 0) < (self.pm1.winner or 0):
                # only if winners are 2/1 and not if winners are 0/0 or None/None
                idx = 0 if idx else 1  # invert
            pm = getattr(self, f"pm{idx + 1}")
            return Slot(content=pm.entry or Unknown())

        # … however, when self._slots has been set through set_slots(), then the order
        # is assumed to be as in the draw. This is because resolve_match_entries()
        # iterates over the van pointers, which are in order by definition:
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
    def status(self) -> TPMatchStatus:
        ret = TPMatchStatus.from_playermatch_status_pair(
            self.pm1.status, self.pm2.status
        )
        logger.debug(f"Status {ret} deduced from {self.pm1!r} and {self.pm2!r}")
        if ret == TPMatchStatus.PENDING:
            if self.is_ready:
                logger.debug("Overriding status for match that is ready")
                return TPMatchStatus.READY
            elif self.is_group_match:
                logger.debug("Overriding status for group match")
                return TPMatchStatus.READY

        return ret

    def _time_repr(self, attr: str) -> str:
        dtobj = getattr(self, attr)
        return (
            repr(dtobj.replace(tzinfo=None)).replace("datetime.", "")
            if dtobj is not None
            else repr(None)
        )

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

    def _status_repr(self) -> str:
        return self.status.name.lower()

    __eq_fields__ = ("pm1", "pm2")
    __str_template__ = (
        "{self.id} [{self.draw.name}] "
        "[{self._van_repr()} → {self._planning_repr()} → {self._wnvn_repr()}] "
        "({self.status})"
    )
    __repr_fields__ = (
        "id",
        "draw.name",
        "matchnr",
        ("time", partial(_time_repr, attr="time"), False),
        ("court", _court_repr, True),
        "slot1?.name",
        "slot2?.name",
        ("planning", _planning_repr, False),
        ("van", _van_repr, False),
        ("wnvn", _wnvn_repr, False),
        ("status", _status_repr, False),
        "winner?.name",
        ("starttime", partial(_time_repr, attr="starttime"), False),
        ("endtime", partial(_time_repr, attr="endtime"), False),
        ("scores", lambda s: scores_to_string(s.scores, nullstr="-"), False),
    )

    __massage_fields__ = {
        "van1": zero_to_none,
        "van2": zero_to_none,
        "winner": zero_to_none,
        "time": partial(normalise_time, nodate_value=datetime(1899, 12, 30)),
    }


mmlogger = logging.getLogger(__name__ + ".matchmaker")


class TPMatchMaker(ReprMixin):
    def __init__(self) -> None:
        self._unmatched: dict[tuple[TPDraw, int], TPPlayerMatch] = {}
        self._matches: dict[tuple[TPDraw, int], TPMatch] = {}
        self._players: dict[tuple[TPDraw, int], TPPlayerMatch] = {}
        self._planning_map: dict[tuple[TPDraw, int], TPMatch] = {}

    def _attr_len_repr(self, name: str) -> str:
        return str(len(getattr(self, name)))

    __repr_fields__ = (
        ("nmatches", partial(_attr_len_repr, name="matches"), False),
        ("nunmatched", partial(_attr_len_repr, name="unmatched"), False),
    )

    def add_playermatch(self, playermatch: TPPlayerMatch) -> None:
        if playermatch.status in (
            TPPlayerMatch.Status.PLAYER,
            TPPlayerMatch.Status.BYE,
        ):
            self._players[playermatch.draw, playermatch.planning] = playermatch
            return

        if (
            other := self._unmatched.pop((playermatch.draw, playermatch.matchnr), None)
        ) is not None:
            if playermatch == other:
                raise ValueError(f"{other} is already registered")

            mmlogger.debug(f"Found match for {playermatch!r}: {other!r}")
            match = TPMatch(pm1=playermatch, pm2=other)
            self._matches[playermatch.draw, playermatch.matchnr] = match

            self._planning_map[match.draw, playermatch.planning] = match
            self._planning_map[match.draw, other.planning] = match
        else:
            mmlogger.debug(f"No pair yet for {playermatch!r}, we will keep looking")
            self._unmatched[playermatch.draw, playermatch.matchnr] = playermatch

        return None

    @property
    def unmatched(self) -> set[TPPlayerMatch]:
        return set(self._unmatched.values())

    @property
    def matches(self) -> set[TPMatch]:
        return set(self._matches.values())

    def resolve_unmatched(self) -> None:
        for pm in sorted(self.unmatched):
            # Gross hack ahead! In draws without e.g. 3/4 playoffs, there are actually
            # not pairs of PlayerMatches. Therefore, we fabricate a fake one, since the
            # Match class expects to work with pairs. The source PlayerMatches will have
            # wv but no vn pointers.
            #
            # First, get any of the preceding player matches. It does not matter which
            # one as the vn pointers should be the same for both. The preceding
            # PlayerMatch is either a match, in which case we obtain pm1, or a player
            srcpm: TPPlayerMatch | None
            if (
                srcmatch := self._planning_map.get((pm.draw, cast(int, pm.van1)))
            ) is not None:
                srcpm = srcmatch.pm1
            else:  # no match found, let's fall back to players
                srcpm = self._players.get((pm.draw, cast(int, pm.van1)))

            if srcpm is not None:
                if (
                    srcpm.wn is not None and srcpm.vn is None
                ):  # pragma: nocover — there is a missed branch here, but I cannot be
                    # bothered.
                    mmlogger.info(f"Fabricating a PlayerMatch to match single {pm!r}")

                    scores = pm.get_scores(reversed=True)
                    sup: dict[str, int] = {}
                    for g, sc in enumerate(scores, 1):
                        sup |= {f"team{t + 1}set{g}": sc[t] for t in range(2)}

                    self.add_playermatch(
                        pm.model_copy(
                            update={
                                "id": -pm.id,
                                "planning": pm.planning + 10000000,
                                "wn": (pm.wn + 10000000) if pm.wn is not None else None,
                                "winner": ((3 - pm.winner) % 3)
                                if pm.winner is not None
                                else None,
                                "entry": None,
                            }
                            | sup
                        )
                    )

            else:
                raise ValueError(f"Cannot resolve unmatched {pm!r}")

    def resolve_match_entries(self) -> None:
        assert len(self.unmatched) == 0, (
            "Cannot resolve entries with unmatched PlayerMatches"
        )

        # Oh my god, what a mess. The TP "database" is a fucking disgrace, full of
        # redundancy and corner cases and inconsistencies.
        #
        # It is entirely unclear what kind of herb the developers of TournamentSoftware
        # were smoking when they designed the database, but I am going to wager that (a)
        # there was no "design" phase anyway, and (b) database, haha. It is remarkable
        # that this shit works.
        #
        # In a nutshell: a "PlayerMatch" is either a player or half of a match, or a
        # match actually. Complete bonkers. Anyway. because of this, we need to
        # dual-pass matches, and resolve the entries on second pass, only to be able to
        # say things like "Martin vs. the Loser of match #4" while match #4 is
        # undecided.
        #
        # To do this, we need to backstep the linked-list created with van1/van2 →
        # planning, rely on the appearance that iff a match is composed of two
        # PlayerMatches, the first actually represents the winner OF THE FUCKING
        # PREVIOUS ROUND, and use the wn/vn forward-pointers to determine this.
        #
        # Without further ado…

        for match in sorted(self.matches):
            slots: list[Slot] = []
            for van in (match.pm1.van1, match.pm1.van2):
                if (srcmatch := self._planning_map.get((match.draw, van or 0))) is None:
                    # There is actually no previous match, so the van pointer points at
                    # a player or a bye.
                    entry = self._players[match.draw, van or 0].entry
                    # if a player, then use the entry, but if the entry is None, then
                    # it's a bye, and we shouldn't have to be dealing with this sort of
                    # detail outside the PlayerMatch class, but it's all fucked up
                    # anyway, so it shall be, and we make a BaseEntry with the "bye"
                    # player:
                    slots.append(Slot(content=entry or Bye()))

                else:
                    # In the case there is a previous match, let's figure out if we come
                    # from its first or second PlayerMatch. If the former, then we are
                    # dealing with the winner. Otherwise the loser:
                    if match.pm1.planning in (srcmatch.pm1.wn, srcmatch.pm1.vn):
                        slots.append(
                            Slot(
                                content=srcmatch.pm1.entry
                                or Playceholder(matchnr=srcmatch.matchnr, winner=True)
                            )
                        )

                    elif match.pm1.planning in (srcmatch.pm2.wn, srcmatch.pm2.vn):
                        slots.append(
                            Slot(
                                content=srcmatch.pm2.entry
                                or Playceholder(matchnr=srcmatch.matchnr, winner=False)
                            )
                        )

                    else:
                        raise ValueError(f"{match} does not derive from {srcmatch}")

            match.set_slots(*slots)
