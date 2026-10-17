from tptools import MatchStatus
from tptools.ext.squore import SquoreCourt, SquoreDraw, SquoreEntry, SquoreMatch


def test_ready_match(sqmatch1: SquoreMatch) -> None:
    assert sqmatch1.status == MatchStatus.READY
    assert isinstance(sqmatch1.draw, SquoreDraw)
    assert isinstance(sqmatch1.court, SquoreCourt)
    assert isinstance(sqmatch1.A, SquoreEntry)
    assert isinstance(sqmatch1.B, SquoreEntry)


def test_pending_match(sqmatch_pending: SquoreMatch) -> None:
    assert sqmatch_pending.status == MatchStatus.PENDING
    assert isinstance(sqmatch_pending.draw, SquoreDraw)
    assert sqmatch_pending.court is None
    assert isinstance(sqmatch_pending.A, SquoreEntry)
    assert sqmatch_pending.B == "Unknown"


def test_squore_match_dump_excludes_errors(sqmatch1: SquoreMatch) -> None:
    """The Squore wire format must not contain the errors array."""
    assert "errors" not in sqmatch1.model_dump()
