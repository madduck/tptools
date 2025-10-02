from enum import IntEnum


class DrawType(IntEnum):
    ELIMINATION = 1
    GROUP = 2
    MONRAD = 3
    # RRHOMEAWAY = 4  # TODO: match-making does not work with this group-type draw
    COMPASS = 5

    @property
    def is_group_draw(self) -> bool:
        return self.value in (
            # DrawType.RRHOMEAWAY,
            DrawType.GROUP,
        )

    @property
    def is_tree_draw(self) -> bool:
        return self.value in (
            DrawType.ELIMINATION,
            DrawType.MONRAD,
            DrawType.COMPASS,
        )
