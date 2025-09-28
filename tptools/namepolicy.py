import dataclasses
from abc import ABC, abstractmethod
from dataclasses import KW_ONLY, dataclass
from typing import Any, Literal, overload

from pydantic import BaseModel, ConfigDict

from .sqlmodels import Court, TPClub, TPCountry, TPPlayer


class ParamsModel(BaseModel):
    # TODO:this does not really belong here
    @classmethod
    def extract_subset(cls, params: "ParamsModel") -> dict[str, Any]:
        return cls.model_validate(dict(params)).model_dump()

    @classmethod
    def make_from_parameter_superset[T: "ParamsModel"](
        cls: type[T], params: "ParamsModel"
    ) -> T:
        return cls(**cls.extract_subset(params))

    __pydantic_config__ = ConfigDict(extra="ignore")


class PairCombinePolicyParams(ParamsModel):
    teamjoinstr: str = "&"
    merge_identical: bool = True


# TODO: remove redundancy between these two classes.
# It currently seems impossible to do so:
# - https://github.com/pydantic/pydantic/discussions/12204
# - https://discuss.python.org/t/dataclasses-asdicttype-type/103448/2


@dataclass(frozen=True)
class PolicyBase(ABC):
    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def params(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PairCombinePolicy(PolicyBase):
    _: KW_ONLY
    teamjoinstr: str = "&"
    merge_identical: bool = True

    def __post_init__(self) -> None:
        if self.teamjoinstr is None:
            raise ValueError("None is not a valid joinstr")

    @overload
    def __call__(
        self, a: str, b: str | None, *, first_can_be_none: Literal[False] = False
    ) -> str: ...

    @overload
    def __call__(
        self, a: str | None, b: str | None, *, first_can_be_none: Literal[True]
    ) -> str | None: ...

    def __call__(self, a, b, *, first_can_be_none=False):  # type: ignore[no-untyped-def]
        if a is None and not first_can_be_none:
            raise ValueError("First in pair cannot be None")

        if self.merge_identical and a == b:
            return a

        return self.teamjoinstr.join(filter(None, (a, b))) or None


@dataclass(frozen=True)
class ClubNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, club: TPClub | None) -> str | None:
        return str(club) if club is not None else None


@dataclass(frozen=True)
class CountryNamePolicy(PolicyBase):
    def __init__(self) -> None: ...

    def __call__(self, country: TPCountry | None) -> str | None:
        return str(country) if country is not None else None


class PlayerNamePolicyParams(ParamsModel):
    fnamemaxlen: int = -1
    namejoinstr: str = " "
    abbrjoinstr: str = "."
    lnamefirst: bool = False
    include_club: bool = False
    include_country: bool = False


# TODO: remove redundancy between these two classes (see above)


@dataclass(frozen=True)
class PlayerNamePolicy(PolicyBase):
    _: KW_ONLY
    fnamemaxlen: int = -1
    namejoinstr: str = " "
    abbrjoinstr: str = "."
    lnamefirst: bool = False
    include_club: bool = False
    include_country: bool = False

    def __call__(
        self,
        player: TPPlayer | None,
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

        name = self._format_name(lname, fname)

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

    def _format_name(self, lname: str, fname: str) -> str:
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


class CourtNamePolicyParams(ParamsModel):
    include_location: bool = False
    no_court_string: str = "No court"


# TODO: remove redundancy between these two classes (see above)


@dataclass(frozen=True)
class CourtNamePolicy(PolicyBase):
    include_location: bool = False
    no_court_string: str = "No court"

    def __call__(self, court: Court | None) -> str:
        if court is None:
            return self.no_court_string

        ret = court.name
        if self.include_location and court.location:
            ret += f" ({court.location})"
        return ret
