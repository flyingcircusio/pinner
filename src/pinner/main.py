from py_dotenv import read_dotenv
import argparse
import copy
import github_api_v3 as github
import json
import logging
import os
import os.path as p
import subprocess

# Main upstream version which we follow. Main branch is 'fc-{TRUNK}-dev'.
# Must be adapted on platform upgrades.
TRUNK = '19.03'

# Repo of our nixpkgs fork and where it has been forked from
NIXPKGS_URL = 'git@github.com:flyingcircusio/nixpkgs'
UPSTREAM_URL = 'https://github.com/NixOS/nixpkgs'

# Repo of our overlay and corresponding API endpoint
FC_NIXOS_URL = 'git@github.com:flyingcircusio/fc-nixos'
API_BASE_URL = 'https://api.github.com/repos/flyingcircusio/fc-nixos'

_log = logging.getLogger(__name__)


class Repository:

    def __init__(self, directory, url):
        self.dir = directory
        self.url = url

    def run(self, *cmd, print_stdout=True, **kw):
        """Executes `cmd` in this repository's workdir."""
        kw.setdefault('cwd', self.dir)
        kw.setdefault('check', True)
        kw.setdefault('stdout', subprocess.PIPE)
        _log.debug('run (%s) %s', kw['cwd'], ' '.join(cmd))
        try:
            stdout = subprocess.run(cmd, **kw).stdout.decode().strip()
        except Exception as e:
            _log.error('>>> %s', e)
            raise
        if stdout and print_stdout:
            _log.debug('>>> %s', stdout)
        return stdout

    def ensure(self):
        if not p.exists(f'{self.dir}/.git'):
            _log.info(f'Cloning {self.url}')
            os.makedirs(self.dir, exist_ok=True)
            self.run('git', 'clone', f'{self.url}.git', self.dir, cwd='.')
        else:
            self.run('git', 'fetch', '--prune')


class Nixpkgs(Repository):

    needs_push = False

    def ensure(self):
        super().ensure()
        self.run('git', 'checkout', f'nixos-{TRUNK}')
        self.run('git', 'reset', '--hard', 'HEAD')
        self.run('git', 'merge', '--ff', f'origin/nixos-{TRUNK}')
        _log.info('Updating upstream refs')
        if f'upstream\t{UPSTREAM_URL}' not in self.run('git', 'remote', '-v'):
            self.run('git', 'remote', 'add', 'upstream', f'{UPSTREAM_URL}.git')
        self.run('git', 'remote', 'update', '-p', 'upstream')

    def query_pinning(self, branch):
        return self.run('git', 'rev-parse', f'upstream/{branch}')

    def query_trunk_pinning(self):
        return self.run('git', 'rev-parse', f'nixos-{TRUNK}')

    def needs_update(self):
        diff = self.run(
            'git', 'log', '--oneline', f'HEAD..upstream/nixos-{TRUNK}')
        if not diff:
            return False
        _log.info(
            'Latest upstream commit not included in origin, update needed')
        return True

    def track_upstream(self):
        if self.needs_update():
            self.run('git', 'merge', '--no-edit', f'upstream/nixos-{TRUNK}')
            self.needs_push = True

    def push(self):
        if self.needs_push:
            _log.warning('Push nixpkgs to origin')
            self.run('git', 'push', 'origin', f'nixos-{TRUNK}')


class FcNixOS(Repository):

    issue_pr = False
    feature_branch = None

    def ensure(self):
        super().ensure()
        self.run('git', 'checkout', f'fc-{TRUNK}-dev')
        self.run('git', 'reset', '--hard', 'HEAD')
        self.run('git', 'merge', f'origin/fc-{TRUNK}-dev')
        self.feature_branch = 'auto-pin-' + \
            self.run('git', 'rev-parse', 'HEAD')[:9]
        self.run('git', 'branch', self.feature_branch, check=False)
        self.run('git', 'checkout', self.feature_branch)
        self.run('git', 'merge', f'fc-{TRUNK}-dev')

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
            sha256 = self.run(
                'nix-prefetch-url', '--unpack',
                f'{UPSTREAM_URL}/archive/{rev}.zip')
            vers_new[branch]['sha256'] = sha256
        _log.info('Creating branch')
        _log.info('Updating pinnings in version.json')
        with open(p.join(self.dir, 'versions.json'), 'w') as f:
            json.dump(vers_new, f, indent=2, sort_keys=True)
            f.write('\n')
        self.run('git', 'add', '.')
        self.run('git', 'commit', '--no-edit', '-m',
                 'Update pinnings of tracked branches',
                 check=False)
        self.issue_pr = True

    def create_pr(self):
        if not self.issue_pr:
            _log.info('Nothing to submit')
            return
        _log.info('Creating fc-nixos pull request')
        self.run('git', 'push', '-u', 'origin', self.feature_branch)
        resp = github.request('POST', API_BASE_URL + '/pulls', {
            'title': '(auto) Update pinnings of tracked branches',
            'head': self.feature_branch,
            'base': f'fc-{TRUNK}-dev',
            'maintainer_can_modify': True,
        })
        _log.debug('>>> %s', resp)
        _log.info('Created pull request: %s', resp.json()['html_url'])


def main():
    # .env should contain GITHUB_TOKEN
    for d in ['.', p.dirname(__file__)]:
        try:
            read_dotenv(p.join(d, '.env'))
            break
        except FileNotFoundError:
            continue
    a = argparse.ArgumentParser()
    a.add_argument('workdir', default='.',
                   help='directory to hold nixpkgs and fc-nixos checkouts')
    a.add_argument('-v', '--verbose', action='store_true', help='more output')
    args = a.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    os.makedirs(args.workdir, exist_ok=True)
    os.chdir(args.workdir)
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
