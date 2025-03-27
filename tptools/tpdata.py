from tptools.entry import Entry
from tptools.playermatch import PlayerMatch
from tptools.tournament import Tournament

ENTRY_QUERY = """
    select e.id as entryid,
    p1.id as player1id, p1.firstname as firstname1,
        p1.name as name1, l1.name as club1, c1.code as country1,
    p2.id as player2id, p2.firstname as firstname2,
        p2.name as name2, l2.name as club2, c2.code as country2
    from
    ( ( ( ( (
                Entry e inner join Player p1 on e.player1 = p1.id
            )
            left outer join Player p2 on e.player2 = p2.id
            )
            left outer join Country c1 on p1.country = c1.id
        )
        left outer join Country c2 on p2.country = c2.id
        )
        left outer join Club l1 on p1.club = l1.id
    )
    left outer join Club l2 on p2.club = l2.id
"""

MATCH_QUERY = """
    select *, m.id as matchid, d.id as drawid,
    d.name as drawname, v.name as eventname,
    c.name as courtname, l.name as locationname
    from
    ( ( (
            PlayerMatch m inner join Draw d on (m.draw = d.id)
        )
        inner join Event v on (d.event = v.id)
        )
        left outer join Court c on (m.court = c.id)
    )
    left outer join Location l on (d.location = l.id)
"""


def load_tournament_from_tpdata(Reader, connstr, *, logger=None, retries=3):
    with Reader(logger=logger) as reader:
        reader.connect(connstr, retries=retries)
        entries = reader.query(ENTRY_QUERY, klass=Entry)
        matches = reader.query(MATCH_QUERY, klass=PlayerMatch)

        return Tournament(entries=entries, playermatches=matches)


async def async_load_tournament_from_tpdata(Reader, connstr, *, logger=None, retries=3):
    async with Reader(logger=logger) as reader:
        await reader.connect(connstr)
        entries = [e async for e in reader.query(ENTRY_QUERY, klass=Entry)]
        matches = [m async for m in reader.query(MATCH_QUERY, klass=PlayerMatch)]

        return Tournament(entries=entries, playermatches=matches)
