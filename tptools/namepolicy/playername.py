from dataclasses import KW_ONLY, dataclass
from typing import overload

from ..entry import Player
from ..paramsmodel import ParamsModel
from .clubname import ClubNamePolicy
from .countryname import CountryNamePolicy
from .policybase import NamePolicy


class PlayerNamePolicyParams(ParamsModel):
    fnamemaxlen: int = -1
    namejoinstr: str = " "
    abbrjoinstr: str = "."
    lnamefirst: bool = False
    include_club: bool = False
    include_country: bool = False


# TODO: remove redundancy between these two classes (see above)
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class PlayerNamePolicy(NamePolicy):
    _: KW_ONLY
    fnamemaxlen: int = -1
    namejoinstr: str = " "
    abbrjoinstr: str = "."
    lnamefirst: bool = False
    include_club: bool = False
    include_country: bool = False

    @overload
    def __call__(
        self,
        player: Player,
        *,
        clubnamepolicy: ClubNamePolicy | None = None,
        countrynamepolicy: CountryNamePolicy | None = None,
    ) -> str: ...

    @overload
    def __call__(
        self,
        player: None,
        *,
        clubnamepolicy: ClubNamePolicy | None = None,
        countrynamepolicy: CountryNamePolicy | None = None,
    ) -> None: ...

    def __call__(
        self,
        player: Player | None,
        *,
        clubnamepolicy: ClubNamePolicy | None = None,
        countrynamepolicy: CountryNamePolicy | None = None,
    ) -> str | None:
        if player is None:
            return None

        fname = player.firstname
        lname = player.lastname
        if not (fname or lname):
            raise ValueError("Need at least a first or a last name")

        name = self._apply_regexps(self._format_name(lname, fname))

        clubnamepolicy = clubnamepolicy or ClubNamePolicy()
        countrynamepolicy = countrynamepolicy or CountryNamePolicy()

        if extra := ", ".join(
            map(
                str,
                filter(
                    None,
                    (
                        clubnamepolicy(player.club) if self.include_club else None,
                        countrynamepolicy(player.country)
                        if self.include_country
                        else None,
                    ),
                ),
            )
        ):
            return f"{name} ({extra})"

        return name

    def _format_name(self, lname: str | None, fname: str) -> str:
        if not lname:
            # fname cannot be None here anymore, but mypy gets confused
            return fname

        elif not fname:
            return lname

        elif self.fnamemaxlen == 0:
            return lname

        elif self.fnamemaxlen < 0 or len(fname) <= self.fnamemaxlen:
            return self.namejoinstr.join(
                (lname, fname) if self.lnamefirst else (fname, lname)
            )

        else:
            fname = fname[: self.fnamemaxlen]
            if self.lnamefirst:
                return self.namejoinstr.join((lname, fname + self.abbrjoinstr.strip()))
            else:
                return self.abbrjoinstr.join((fname, lname))
