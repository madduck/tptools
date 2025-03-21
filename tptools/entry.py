class Entry(dict):
    COMPKEYS = ("name1", "firstname1", "name2", "firstname2")

    @staticmethod
    def make_team_name(players, *, joinstr="&"):
        if len(players) == 1:
            return players[0]
        elif len(players) == 2 and players[0] == players[1]:
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

    def _is_valid_operand(self, other):
        return all(comp in other for comp in self.COMPKEYS)

    def _comp(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented

        a = " ".join(self[comp] or "" for comp in self.COMPKEYS)
        b = " ".join(other[comp] or "" for comp in self.COMPKEYS)

        return a, b

    def __lt__(self, other):
        pair = self._comp(other)
        return pair[0] < pair[1]

    def __le__(self, other):
        pair = self._comp(other)
        return pair[0] <= pair[1]

    def __gt__(self, other):
        pair = self._comp(other)
        return pair[0] > pair[1]

    def __ge__(self, other):
        pair = self._comp(other)
        return pair[0] >= pair[1]

    def __eq__(self, other):
        pair = self._comp(other)
        return pair[0] == pair[1]

    def __ne__(self, other):
        pair = self._comp(other)
        return pair[0] != pair[1]

    def get_players(self, *, short=False):
        def make_name(first, last, short):
            if not first:
                return last
            elif not last:
                return first
            elif short:
                return f"{first[0]}.{last}"
            else:
                return f"{first} {last}"

        ret = make_name(self["firstname1"], self["name1"], short)
        if n2 := self.get("name2"):
            return (ret, make_name(self["firstname2"], n2, short))
        else:
            return (ret,)

    id = property(lambda s: s["entryid"])
    players = property(lambda s: s.get_players())
    playersshort = property(lambda s: s.get_players(short=True))

    def get_fields(self, field):
        ret = self[f"{field}1"]
        if c2 := self.get(f"{field}2"):
            return (ret, c2)
        else:
            return (ret,)

    countries = property(lambda s: s.get_fields("country"))
    clubs = property(lambda s: s.get_fields("club"))
