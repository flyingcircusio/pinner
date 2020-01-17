import subprocess
import argparse
import json
import os
import os.path as p

RO_PREFIX = 'https://github.com/'
RW_PREFIX = 'git@github.com:'


class Upstream:

    def __init__(self, name, url):
        self.name = name
        self.url = url


class Repos:
    MAIN_URL = 'git@github.com:flyingcircusio/fc-nixos.git'
    TRACK_URL = 'git@github.com:flyingcircusio/nixpkgs.git'

    def __init__(self):
        self.repos = {'fc-nixos': self.MAIN_URL, 'nixpkgs': self.TRACK_URL}

    def fetch_versions(self):
        self.init_repos()
        self.update_upstreams()
        self.versions = json.load(open(p.join('fc-nixos', 'versions.json')))

    def init_repos(self):
        if p.exists('fc-nixos'):
            subprocess.run(['git', 'clone', '-n', self.MAIN_URL], check=True)

    def update_upstreams(self):
        pass


def main():
    a = argparse.ArgumentParser()
    a.add_argument('basedir', default='.')
    args = a.parse_args()
    os.chdir(args.basedir)


if __name__ == '__main__':
    main()
