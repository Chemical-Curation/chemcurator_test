"""
chemcurator_test.py - set up test env. for Chem Curator

This is a "bash script" written in Python, not a Python program.
Because... no one ever remembers bash array syntax.  And this is
a Python project.

Terry N. Brown Brown.TerryN@epa.gov Wed 23 Dec 2020 09:43:54 PM UTC
"""
import argparse
import os
import subprocess
from hashlib import sha256
from pathlib import Path

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
        git(repo, ["clone", _config("GIT_BASE_URL").format(auth=auth) + repo])


def make_parser():

    top_parser = argparse.ArgumentParser(
        description="Spin up ChemCurator test env."
    )
    subparsers = top_parser.add_subparsers()
    table = [
        ("list", []),
        ("co", ["repo", "branch"]),
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


def cmd_list(opt):
    for repo in TEST_BRANCH:
        git(repo, ("branch -a"))


def cmd_co(opt):
    git(opt.repo, (f"checkout {opt.branch}"))


def cmd_up(opt):
    pass


def cmd_down(opt):
    pass


def main():
    opt = get_options()
    print(get_base_port())
    opt.func(opt)


if __name__ == "__main__":
    main()
