import re

R_DRVNAME = re.compile(r'^(.*?)-(\d.*)$')


def parsedrvname(name):
    m = R_DRVNAME.match(name)
    if m:
        return tuple(m.groups())
    return (name, '')


class Packageset:

    pkgs = None

    @classmethod
    def parse(cls, nixenv_p):
        self = cls()
        self.pkgs = {}
        for line in nixenv_p.splitlines():
            attr, name = line.strip().split(None, 2)
            self.pkgs[attr] = parsedrvname(name)
        return self

    def diff(self, other):
        updated = {}
        removed = {}
        added = {}
        for k, val in self.pkgs.items():
            if k in other.pkgs:
                other_val = other.pkgs[k]
                if val != other_val:
                    updated[k] = '{} -> {}'.format(
                        '-'.join(val), '-'.join(other_val))
            else:
                added[k] = '-'.join(val)
        for k, val in other.pkgs.items():
            if k not in self.pkgs:
                removed[k] = '-'.join(val)
        return {
            'updated': updated,
            'removed': removed,
            'added': added,
        }

