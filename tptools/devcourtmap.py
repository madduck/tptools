import logging
import re
import tomllib
from collections.abc import Iterable
from typing import IO, Never

from tptools.court import Court
from tptools.util import flatten_dict

logger = logging.getLogger(__name__)


class DeviceCourtMap:
    def __init__(self, tomlfile: IO[bytes] | None = None) -> None:
        self._devmap: dict[str, int | str] = (
            {} if tomlfile is None else self.read_toml_devmap(tomlfile)
        )

    @staticmethod
    def read_toml_devmap(tomlfile: IO[bytes]) -> dict[str, int | str] | Never:
        devmap: dict[str, int | str] = tomllib.load(tomlfile)

        # TOML turns a key like 172.21.22.1 into a nested dict {"172":{"21":{"22"…}…}…}
        # so for convenience, flatten this:
        return flatten_dict(devmap)

    @staticmethod
    def normalise_court_name_for_matching(
        courtname: str,
    ) -> tuple[int | None, int] | None:
        m = re.match(
            r"(?:-?(?P<loc>\d+)-)?c(?:ourt *)?0*(?P<court>\d+)",
            courtname,
            flags=re.IGNORECASE,
        )
        if m:
            return int(loc) if (loc := m["loc"]) is not None else None, int(m["court"])
        else:
            return None

    def find_court_for_ip(
        self, clientip: str, courts: Iterable[Court] | None = None
    ) -> Court | None:
        courtname = None
        if (courtname := self._devmap.get(clientip)) is not None:
            logger.debug(f"Device at IP {clientip} might be on {courtname}")
            for court in courts or []:
                # TODO: can we do better than this to identify the court when we are
                # given a string that might not be what the current courtnamepolicy
                # returns, or an ID?
                if isinstance(courtname, int):
                    if courtname == court.id:
                        return court

                else:
                    term = self.normalise_court_name_for_matching(courtname)
                    if term is not None:
                        comps = (
                            []
                            if court.location is None
                            else [
                                f"{court.location.id}-{court.name}",
                                f"{court.location.id}-{court}",
                            ]
                        )

                        for comparename in (
                            *comps,
                            court.name,
                            str(court),
                        ):
                            comp = self.normalise_court_name_for_matching(comparename)
                            if (
                                comp is not None
                                and (term[0] is None and term[1] == comp[1])
                                or (term == comp)
                            ):
                                return court

        logger.debug(f"No court found in devmap for device with IP {clientip}")
        return None

    def find_match_for_ip(self, clientip: str) -> str | None:
        text = self._devmap.get(clientip)
        return str(text) if text is not None else None
