from typing import Any, cast


class StrMixin:
    __str_template__: str | None = None

    def __init_subclass__(cls, *args: Any, **kwargs: Any) -> None:
        super().__init_subclass__(*args, **kwargs)

    def __str__(self) -> str:
        if self.__str_template__ is None:
            return super().__str__()

        else:
            return cast(
                str, eval(f'f"""{self.__str_template__}"""', locals={"self": self})
            )
