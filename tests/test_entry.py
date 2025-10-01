from tptools import Entry


def test_repr(entry1: Entry) -> None:
    assert repr(entry1) == "Entry(event.name='Herren 1', player1.name='Martin Krafft')"


def test_repr_doubles(entry12: Entry) -> None:
    assert repr(entry12) == (
        "Entry(event.name='Herren 1', "
        "player1.name='Martin Krafft', "
        "player2.name='Iddo Hoeve')"
    )


def test_str(entry1: Entry) -> None:
    assert str(entry1) == "Martin Krafft (RSC, Deutschland)"


def test_str_doubles(entry12: Entry) -> None:
    assert str(entry12) == (
        "Martin Krafft (RSC, Deutschland)&Iddo Hoeve (SomeClub, Holland)"
    )


def test_cmp_eq(entry1: Entry, entry1copy: Entry) -> None:
    assert entry1 == entry1copy


def test_cmp_ne(entry1: Entry, entry2: Entry) -> None:
    assert entry1 != entry2


def test_cmp_lt(entry1: Entry, entry2: Entry) -> None:
    assert entry2 < entry1


def test_cmp_le(entry1: Entry, entry1copy: Entry, entry2: Entry) -> None:
    assert entry2 < entry1 and entry1 <= entry1copy


def test_cmp_gt(entry1: Entry, entry2: Entry) -> None:
    assert entry1 > entry2


def test_cmp_ge(entry1: Entry, entry1copy: Entry, entry2: Entry) -> None:
    assert entry1 > entry2 and entry1 >= entry1copy
