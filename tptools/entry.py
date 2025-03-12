class Entry(dict):

    @staticmethod
    def make_team_name(players, *, joinstr="&"):
        if len(players) == 1 or (
            len(players) == 2 and players[0] == players[1]
        ):
            return players[0]
        ret = joinstr.join([str(p) for p in players if p is not None])
        return ret or None

    def __repr__(self):
        if entryid := self.get("entryid"):
            return f'<Entry ID {entryid} "{self!s}">'
        else:
            return f"<Entry {self!s}>"

    def __str__(self):
        return Entry.make_team_name(self.get_players(short=True))

    def get_players(self, *, short=False):
        def make_name(first, last, short):
            if short:
                return f"{first[0]}.{last}"
            else:
                return f"{first} {last}"

        ret = make_name(self["firstname1"], self["name1"], short)
        if (n2 := self.get("name2")):
            return (ret, make_name(self['firstname2'], n2, short))
        else:
            return (ret,)

    id = property(lambda s: s['entryid'])
    players = property(lambda s: s.get_players())
    playersshort = property(lambda s: s.get_players(short=True))

    def get_fields(self, field):
        ret = self[f'{field}1']
        if (c2 := self.get(f'{field}2')):
            return (ret, c2)
        else:
            return (ret,)

    countries = property(lambda s: s.get_fields("country"))
    clubs = property(lambda s: s.get_fields("club"))
