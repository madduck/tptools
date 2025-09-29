import logging
from functools import partial
from typing import cast

from .mixins.repr import ReprMixin
from .playermatchstatus import PlayerMatchStatus
from .slot import Bye, Playceholder, Slot
from .sqlmodels import TPDraw, TPPlayerMatch
from .tpmatch import TPMatch

logger = logging.getLogger(__name__)


class MatchMaker(ReprMixin):
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
        if playermatch.status in (PlayerMatchStatus.PLAYER, PlayerMatchStatus.BYE):
            self._players[playermatch.draw, playermatch.planning] = playermatch
            return

        if (
            other := self._unmatched.pop((playermatch.draw, playermatch.matchnr), None)
        ) is not None:
            if playermatch == other:
                raise ValueError(f"{other} is already registered")

            logger.debug(f"Found match for {playermatch!r}: {other!r}")
            match = TPMatch(pm1=playermatch, pm2=other)
            self._matches[playermatch.draw, playermatch.matchnr] = match

            self._planning_map[match.draw, playermatch.planning] = match
            self._planning_map[match.draw, other.planning] = match
        else:
            logger.debug(f"No pair yet for {playermatch!r}, we will keep looking")
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
                    logger.info(f"Fabricating a PlayerMatch to match single {pm!r}")
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
