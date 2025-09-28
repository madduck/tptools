from typing import Any

from pydantic import BaseModel, ConfigDict


class ParamsModel(BaseModel):
    @classmethod
    def extract_subset(cls, params: "ParamsModel") -> dict[str, Any]:
        return cls.model_validate(dict(params)).model_dump()

    @classmethod
    def make_from_parameter_superset[T: "ParamsModel"](
        cls: type[T], params: "ParamsModel"
    ) -> T:
        return cls(**cls.extract_subset(params))

    __pydantic_config__ = ConfigDict(extra="ignore")
