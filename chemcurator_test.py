"""
chemcurator_test.py - set up test env. for Chem Curator

This is a "bash script" written in Python, not a Python program.
Because... no one ever remembers bash array syntax.  And ChemCurator is
a Python project.

Goal: automate deployment of the chemcurator_django, chemcurator_vuejs,
resolver, and DB services in a single private docker network for testing
and PR approval.

Unfortunately we can't incorporate the resolver/docker-compose.yml file with
docker-compose --file resolver/docker-compose.yml --file docker-compose.yml
because this will just merge, not replace, the port settings, leaving 5000
in use even though we don't want that.  So changes in
resolver/docker-compose.yml will need to be merged into docker.compose.yml.

Docker env. variable management is a product of evolution, like the platypus.

According to https://docs.docker.com/compose/environment-variables/,
environment variable priority, from high to low, is:

1. Compose file
2. Shell environment variables
3. Environment file
4. Dockerfile
5. Variable is not defined

Testing shows that whe the are multiple environment files, all are loaded, when
there are overlapping values, the last in the list wins.

To allow for out of date docker-compose versions, we'll just use .env.

Terry N. Brown Brown.TerryN@epa.gov Wed 23 Dec 2020 09:43:54 PM UTC
"""
import argparse
import os
import subprocess
import time
from hashlib import sha256
from pathlib import Path

import yaml

DOCKER_REPOS = 'resolver', 'chemcurator_vuejs', 'chemcurator_django'

try:
    import chemcurator_test_config as CONFIG
except ImportError:
    print(
        """
Couldn't load config from chemcurator_test_config.py, copy
chemcurator_test_config.py.template to chemcurator_test_config.py,
edit, and retry.
"""
    )
    exit(10)

# repo / branch mapping for "default" branches, so we can reset to defaults
# and then checkout a PR branch in one or more repos.
TEST_BRANCH = {
    "chemcurator_django": "dev",
    "chemcurator_vuejs": "dev",
    "resolver": "dev",
    "ketcher": "master",
}
TEST_BRANCH.update(getattr(CONFIG, "TEST_BRANCH", {}))

CMDS = []  # list of "commands" the test env. can run


def _config(key):
    return os.environ.get(key) or getattr(CONFIG, key, None)


def get_base_port():
    if _config("BASE_PORT"):
        return int(_config("BASE_PORT"))
    return (
        32768
        + int.from_bytes(
            sha256(os.environ['USER'].encode('utf8')).digest()[:4],
            'big',
            signed=False,
        )
        % 16384
    )


def git(repo, cmd):
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    if cmd.startswith("clone "):
        cmd = f"git {cmd}"
    else:
        cmd = f"git -C {repo} {cmd}"
    print(cmd)
    subprocess.Popen(cmd, shell=True).communicate()


# check repos are here, clone if not
auth = _config("GIT_USER")
token = _config("GIT_TOKEN")
if auth is not None and token is not None:
    auth = f"{auth}:{token}"
for repo in TEST_BRANCH:
    if not Path(repo).exists():
        git(
            repo,
            ["clone", _config("GIT_BASE_URL").format(auth=auth or "") + repo],
        )


def make_parser():

    top_parser = argparse.ArgumentParser(
        description="Spin up ChemCurator test env."
    )
    subparsers = top_parser.add_subparsers()
    table = [
        ("list", []),
        ("co", ["repo", "branch"]),
        ("build", []),
        ("up", []),
        ("down", []),
    ]
    for cmd, params in table:
        parser = subparsers.add_parser(cmd)
        parser.set_defaults(func=globals()[f"cmd_{cmd}"])
        for param in params:
            parser.add_argument(param)

    return top_parser


def get_options(args=None):
    """
    get_options - use argparse to parse args, and return a
    argparse.Namespace, possibly with some changes / expansions /
    validations.

    Client code should call this method with args as per sys.argv[1:],
    rather than calling make_parser() directly.

    Args:
        args ([str]): arguments to parse

    Returns:
        argparse.Namespace: options with modifications / validations
    """
    opt = make_parser().parse_args(args)

    # modifications / validations go here

    return opt


def get_exposed_ports():
    base_port = get_base_port()
    ports = [
        'POSTGRES_DB_PORT',
        'RESOLVER_PORT',
        'VUE_APP_PORT',
        'DJANGO_APP_PORT',
    ]

    return {'EX_' + i: base_port + n for n, i in enumerate(ports)}


def get_env():
    env = []
    for path in DOCKER_REPOS:
        env.extend(["", "#" * 60, f"# template.env from {path}", "#" * 60, ""])
        env.extend([i.rstrip('\n') for i in open(f"{path}/template.env")])
    env.extend(["", "#" * 60, "# chemcurator_test settings", "#" * 60, ""])
    env.extend([f"{k}={v}" for k, v in get_exposed_ports().items()])

    return env


def get_docker_compose():

    dc = yaml.safe_load(
        open(
            os.path.join(
                os.path.dirname(__file__), 'resolver', 'docker-compose.yml'
            )
        )
    )
    # dc['services']['web']['container_name'] = 'resolver'
    dc['services']['web']['ports'] = ["${EX_RESOLVER_PORT}:${RESOLVER_PORT}"]
    dc['services']['web']['build'] = {"context": "./resolver/"}
    dc['services']['web']['volumes'] = [
        "./resolver/migrations:/code/migrations",
        "./resolver/resolver:/code/resolver",
    ]
    dc['services']['db']['ports'] = [
        "${EX_POSTGRES_DB_PORT}:${POSTGRES_DB_PORT}"
    ]
    user = os.environ['USER']
    dc['services']['db']['volumes'] = [
        f"{user}_resolver_postgres_data:/var/lib/postgresql/data/"
    ]
    dc['volumes'] = {f"{user}_resolver_postgres_data": None}
    return dc


def cmd_list(opt):
    for repo in TEST_BRANCH:
        git(repo, ("branch -a"))


def cmd_co(opt):
    git(opt.repo, (f"checkout {opt.branch}"))


def cmd_build(opt):
    old_cd = os.getcwd()


def cmd_up(opt):
    with open('.env', 'w') as out:
        ts = time.asctime()
        out.write(f"# AUTOMATICALLY GENERATED {ts}\n")
        out.write("# DO NOT EDIT\n\n")
        out.write('\n'.join(get_env()))
    with open('docker-compose.yml', 'w') as out:
        ts = time.asctime()
        out.write(f"# AUTOMATICALLY GENERATED {ts}\n")
        out.write("# DO NOT EDIT\n\n")
        out.write(yaml.dump(get_docker_compose()))


def cmd_down(opt):
    pass


def main():
    opt = get_options()
    opt.func(opt)


if __name__ == "__main__":
    main()
