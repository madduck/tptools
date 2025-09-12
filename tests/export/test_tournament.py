from tptools.export import Court, Draw, Entry, Tournament


def test_repr(exptournament1: Tournament) -> None:
    assert (
        repr(exptournament1)
        == "Tournament(tpdata=TPData(name='Test 1', nentries=2, nmatches=2))"
    )


def test_str(exptournament1: Tournament) -> None:
    assert str(exptournament1) == "Test 1 (2 entries, 2 matches)"


def test_get_entries(exptournament1: Tournament, expentry1: Entry) -> None:
    entries: dict[int, Entry] = exptournament1.get_entries()
    assert len(entries) == 2
    assert expentry1 == entries[expentry1.id]


def test_get_entries_cache(exptournament1: Tournament) -> None:
    entries: dict[int, Entry] = exptournament1.get_entries()
    assert entries is exptournament1.get_entries()


def test_resolve_entry(exptournament1: Tournament, expentry1: Entry) -> None:
    assert exptournament1.resolve_entry_by_id(expentry1.id) == expentry1


def test_get_courts(exptournament1: Tournament, expcourt1: Court) -> None:
    courts: dict[int, Court] = exptournament1.get_courts()
    assert len(courts) == 1
    assert expcourt1 == courts[expcourt1.id]


def test_get_courts_cache(exptournament1: Tournament) -> None:
    courts: dict[int, Court] = exptournament1.get_courts()
    assert courts is exptournament1.get_courts()


def test_resolve_court(exptournament1: Tournament, expcourt1: Court) -> None:
    assert exptournament1.resolve_court_by_id(expcourt1.id) == expcourt1


def test_get_draws(exptournament1: Tournament, expdraw1: Draw) -> None:
    courts: dict[int, Draw] = exptournament1.get_draws()
    assert len(courts) == 1
    assert expdraw1 == courts[expdraw1.id]


def test_get_draws_cache(exptournament1: Tournament) -> None:
    courts: dict[int, Draw] = exptournament1.get_draws()
    assert courts is exptournament1.get_draws()


def test_resolve_draw(exptournament1: Tournament, expdraw1: Draw) -> None:
    assert exptournament1.resolve_draw_by_id(expdraw1.id) == expdraw1


def test_model_dump(exptournament1: Tournament) -> None:
    dump = exptournament1.model_dump()
    for field in ("name", "matches", "entries"):
        assert field in dump
