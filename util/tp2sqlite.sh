#!/bin/sh
#
# Read TournamentSoftware TP file, generate SQlite commands to clone the database
# into something more usable than Microsoft Stupid Access
#
# Usage: ./tp2sqlite.sh ../path/to/Tournament.TP [-a|--all] | sqlite3 database.sqlite
#
set -eu

all=0
mdbfile=
for arg in "$@"; do
  case "$arg" in
  -a | --all) all=1 ;;
  *)
    if [ -z "${mdbfile:-}" ]; then
      mdbfile="$arg"
    else
      echo >&2 "Unknown argument: $arg"
      exit 1
    fi
    ;;
  esac
done

for table in $(mdb-tables "$mdbfile"); do
  case "$table" in
  Availability)
    echo >&2 "  Skipping table: $table… (cannot process binary blobs)"
    continue
    ;;
  Country | Club | Player | Entry | PlayerMatch | Draw | stage | Event | Court | Location | ScoringFormat | Settings) ;;
  *)
    if [ $all = 0 ]; then
      echo >&2 "  Skipping table: $table… (not currently relevant)"
      continue
    fi
    ;;
  esac

  echo >&2 -n "Processing table: $table… "

  mdb-schema --drop-table -T "$table" "$mdbfile" sqlite | grep -v '^--' || :
  echo >&2 -n "schema… "
  mdb-export -D "%Y-%m-%d %H:%M:%S" -H -I sqlite "$mdbfile" "$table" | grep -v '^--' || :
  echo >&2 -n "data… "

  anon=1
  case "$table" in
  Payment | usagelog | Log)
    echo "DELETE FROM $table;"
    ;;
  Player)
    cat <<-_eof
		UPDATE Player SET
      name = concat(substr(name, 1, 1), '.'),
		  address = 'Some Street 123',
		  postalcode = 81234,
		  city = 'München',
		  state = 'Bayern',
		  phone = '+491234567890',
		  mobile = '+491234567890',
		  office = '+491234567890',
		  fax = '+491234567890',
		  email = 'player@example.org',
		  dob = '1970-01-01 12:34:56',
		  memberid = 12345,
		  memo = null;
		_eof
    ;;
  *) anon=0 ;;
  esac
  [ $anon = 0 ] || echo >&2 -n "anonymising… "

  echo >&2 done.
done

echo >&2 -n "Making views… "

cat <<_eof
drop view if exists PlayerMatchView;
create view PlayerMatchView as
  select
    m.id,
    v.name as event, d.name as draw, d.drawtype, d.drawsize,
    m.matchnr,
    m.entry as entryid, p.firstname, p.name,
    m.planning, m.van1, m.van2, m.wn, m.vn,
    m.reversehomeaway,
    m.plandate as time,
    m.winner,
    concat_ws(', ',
      concat_ws('-', team1set1, team2set1),
      concat_ws('-', team1set2, team2set2),
      concat_ws('-', team1set3, team2set3),
      concat_ws('-', team1set4, team2set4),
      concat_ws('-', team1set5, team2set5)
    ) as score,
    m.walkover, m.retired
  from  ( ( (
            PlayerMatch m inner join Draw d on (m.draw = d.id)
        )
        inner join Event v on (d.event = v.id)
      )
      left outer join Entry e on (m.entry = e.id)
    )
    left outer join Player p on (e.player1 = p.id)
  order by event, draw, planning;

drop view if exists MatchView;
create view MatchView as
  select
    p1.id as id1, p2.id as id2,
    p1.drawid,
    p1.matchnr,
    p1.entryid as e1, p1.firstname as fname1, p1.name as lname1,
    p2.entryid as e2, p2.firstname as fname2, p2.name as lname2,
    p1.planning as planning1, p2.planning as planning2,
    p1.van1, p1.van2,
    p1.wn as wn1, p1.vn as vn1,
    p2.wn as wn2, p2.vn as vn2,
    p1.winner as w1, p2.winner as w2,
    p1.score as sc1, p2.score as sc2
  from PlayerMatchView p1
    right outer join PlayerMatchView p2
      on (
        p1.drawid == p2.drawid
        and p1.matchnr == p2.matchnr
        and p1.matchnr > 0
        and p1.id < p2.id
      )
  union
    select id, null,
      drawid,
      matchnr,
      entryid, firstname, name,
      null, null, null,
      planning, null,
      null, null,
      wn, vn,
      null, null,
      null, null,
      null, null
    from PlayerMatchView
      where matchnr == 0;

_eof

echo >&2 done.
