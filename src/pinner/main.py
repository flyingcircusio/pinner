import argparse
import copy
import json
import logging
import os
import os.path as p
import subprocess

TRUNK = '19.03'
NIXPKGS_URL = 'git@github.com:flyingcircusio/nixpkgs'
FC_NIXOS_URL = 'git@github.com:ckauhaus/fc-nixos'
UPSTREAM_URL = 'https://github.com/NixOS/nixpkgs'

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

    def __init__(self, directory, url):
        self.dir = directory
        self.url = url

    def ensure(self):
        if not p.exists(f'{self.dir}/.git'):
            _log.info(f'Cloning {self.url}.git')
            run('git', 'clone', self.url, self.dir)
        else:
            run('git', 'fetch', '--prune', cwd=self.dir)


class Nixpkgs(Repository):

    needs_push = False

    def ensure(self):
        super().ensure()
        run('git', 'checkout', f'nixos-{TRUNK}', cwd=self.dir)
        run('git', 'reset', '--hard', 'HEAD', cwd=self.dir)
        run('git', 'merge', '--ff', f'origin/nixos-{TRUNK}', cwd=self.dir)
        _log.info('Updating upstream refs')
        if f'upstream\t{UPSTREAM_URL}' not in run(
                'git', 'remote', '-v', cwd='nixpkgs'):
            run('git', 'remote', 'add', 'upstream', f'{UPSTREAM_URL}.git',
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
        return run('git', 'rev-parse', f'upstream/{branch}', cwd=self.dir)

    def query_trunk_pinning(self):
        return run('git', 'rev-parse', f'nixos-{TRUNK}', cwd=self.dir)

    def push(self):
        if self.needs_push:
            _log.warning('Push nixpkgs to origin')
            run('git', 'push', 'origin', f'nixos-{TRUNK}', cwd=self.dir)


class FcNixOS(Repository):

    issue_pr = False

    def ensure(self):
        super().ensure()
        run('git', 'checkout', f'fc-{TRUNK}-dev', cwd=self.dir)
        run('git', 'reset', '--hard', 'HEAD', cwd=self.dir)
        run('git', 'merge', '--ff', f'origin/fc-{TRUNK}-dev', cwd=self.dir)

    def update_pinnings(self, nixpkgs):
        vers = json.load(open(p.join(self.dir, 'versions.json')))
        vers_new = copy.deepcopy(vers)
        for branch in vers:
            if branch.startswith('nixos-'):
                pin = nixpkgs.query_pinning(branch)
                vers_new[branch]['rev'] = pin
            elif branch == 'nixpkgs':
                pin = nixpkgs.query_trunk_pinning()
                vers_new[branch]['rev'] = pin
        if vers == vers_new:
            return
        _log.info('Updating SHA256 checksums')
        for branch in vers_new:
            if not branch.startswith('nixos-'):
                continue
            rev = vers_new[branch]['rev']
            if rev == vers[branch]['rev']:
                continue
            sha256 = run(
                'nix-prefetch-url', '--unpack',
                f'{UPSTREAM_URL}/archive/{rev}.zip')
            vers_new[branch]['sha256'] = sha256
        _log.info('Updating pinnings in version.json')
        with open(p.join(self.dir, 'versions.json'), 'w') as f:
            json.dump(vers_new, f, indent=2, sort_keys=True)
        self.issue_pr = True

    def create_pr(self):
        if self.issue_pr:
            _log.warning('create fc-nixos pull request')
            run('git', 'checkout', '-b', 'update-versions', cwd=self.dir)
            run('git', 'commit', '--no-edit', '-m',
                '[auto] Update versions of tracked branches')


def main():
    a = argparse.ArgumentParser()
    a.add_argument('basedir', default='.')
    args = a.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    os.makedirs(args.basedir, exist_ok=True)
    os.chdir(args.basedir)
    nixpkgs = Nixpkgs('nixpkgs', NIXPKGS_URL)
    nixpkgs.ensure()
    nixpkgs.track_upstream()
    fc_nixos = FcNixOS('fc-nixos', FC_NIXOS_URL)
    fc_nixos.ensure()
    fc_nixos.update_pinnings(nixpkgs)
    nixpkgs.push()
    fc_nixos.create_pr()


if __name__ == '__main__':
    main()
