import argparse
import copy
import json
import logging
import os
import os.path as p
import subprocess

TRUNK = '19.03'
NIXPKGS_URL = 'git@github.com:flyingcircusio/nixpkgs.git'
FC_NIXOS_URL = 'git@github.com:flyingcircusio/fc-nixos.git'
UPSTREAM_URL = 'https://github.com/NixOS/nixpkgs.git'

_log = logging.getLogger(__name__)


def run(*cmd, **kw):
    if 'cwd' in kw:
        dirinfo = f"({kw['cwd']}) "
    else:
        dirinfo = ''
    _log.debug('run %s%s', dirinfo, ' '.join(cmd))
    kw.setdefault('check', True)
    kw.setdefault('stdout', subprocess.PIPE)
    stdout = subprocess.run(cmd, **kw).stdout.decode().strip()
    if stdout:
        _log.debug('>>> %s', stdout)
    return stdout


class Repository:

    needs_push = False

    def __init__(self, directory, url):
        self.dir = directory
        self.url = url

    def ensure(self):
        if not p.exists(f'{self.dir}/.git'):
            _log.info(f'Cloning {self.url}')
            run('git', 'clone', self.url, self.dir)
        else:
            run('git', 'fetch', '--prune', cwd=self.dir)


class Nixpkgs(Repository):

    pin_nixpkgs = None

    def ensure(self):
        super().ensure()
        run('git', 'checkout', f'nixos-{TRUNK}', cwd=self.dir)
        run('git', 'merge', '--ff', f'origin/nixos-{TRUNK}', cwd=self.dir)
        _log.info('Updating upstream refs')
        if f'upstream\t{UPSTREAM_URL}' not in run(
                'git', 'remote', '-v', cwd='nixpkgs'):
            run('git', 'remote', 'add', 'upstream', self.UPSTREAM_URL,
                cwd='nixpkgs')
        run('git', 'remote', 'update', '-p', 'upstream', cwd=self.dir)

    def needs_update(self):
        diff = run(
            'git', 'log', '--oneline',
            f'HEAD..upstream/nixos-{TRUNK}', cwd=self.dir)
        if not diff:
            return False
        _log.info(
            'Latest upstream commit not included in origin, update needed')
        return True

    def track_upstream(self):
        if self.needs_update():
            run('git', 'merge', '--no-edit', f'upstream/nixos-{TRUNK}',
                cwd=self.dir)
            self.needs_push = True

    def query_pinning(self, branch):
        return ''

    def query_trunk_pinning(self):
        return run('get', 'rev-parse', 'nixos-{TRUNK}', cwd=self.dir)


class FcNixOS(Repository):

    def ensure(self):
        super().ensure()
        run('git', 'checkout', f'fc-{TRUNK}-dev', cwd=self.dir)
        run('git', 'merge', '--ff', f'origin/fc-{TRUNK}-dev', cwd=self.dir)

    def update_pinnings(self, nixpkgs):
        _log.info('Update pinnings in version.json')
        vers = json.load(open(p.join(self.dir, 'versions.json')))
        vers_new = copy.deepcopy(vers)
        for branch in vers:
            if branch.startswith('nixos-'):
                pin = nixpkgs.query_pinning(branch)
                vers_new[branch]['rev'] = pin
            elif branch == 'nixpkgs':
                pin = nixpkgs.query_trunk_pinning()
                vers_new[branch]['rev'] = pin
        # XXX if vers != vers_new


def main():
    a = argparse.ArgumentParser()
    a.add_argument('basedir', default='.')
    args = a.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    os.chdir(args.basedir)
    nixpkgs = Nixpkgs('nixpkgs', NIXPKGS_URL)
    nixpkgs.ensure()
    nixpkgs.track_upstream()
    fc_nixos = FcNixOS('fc-nixos', FC_NIXOS_URL)
    fc_nixos.ensure()
    fc_nixos.update_pinnings(nixpkgs)


if __name__ == '__main__':
    main()
