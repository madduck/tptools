import logging

from pydantic import Field

from .basemodel import SqModel
from .match import SquoreMatch

logger = logging.getLogger(__name__)


class MatchesSection(SqModel):
    name: str
    # Sorting in Squore is inconsistent. A hack is to prefix the section names
    # with a non-breaking space.
    nameprefix: str = "\xa0"
    expanded: bool = False
    expandprefix: str = "+"
    matches: list[SquoreMatch] = Field(default_factory=list)

    def _get_matches_len(self) -> int:
        return len(self.matches)

    __str_template__ = (
        "{self.get_name_expanding() if self.expanded else self.get_name()}"
    )
    __repr_fields__ = ("name", ("nmatches", _get_matches_len, False), "expanded")

    def get_name(self) -> str:
        return f"{self.nameprefix}{self.name}"

    def get_name_expanding(self) -> str:
        return f"{self.expandprefix}{self.get_name()}"
