from typing import Any

from sqlmodel import SQLModel

from .mixins import ComparableMixin, ReprMixin, StrMixin


class Model(ReprMixin, StrMixin, ComparableMixin, SQLModel):
    def __setattr__(self, attr: str, value: Any) -> None:
        if hasattr(self, f"{attr}id_") and hasattr(value, "id"):
            object.__setattr__(self, f"{attr}id_", value.id)
        super().__setattr__(attr, value)

    # TODO: a model_serializer that adds Relationships which generate a model
    # themselves, not a list.
