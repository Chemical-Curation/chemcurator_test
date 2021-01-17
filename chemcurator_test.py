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

# places to collect template.env from
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


class IndentLists(yaml.Dumper):
    """https://stackoverflow.com/a/39681672/1072212
    Default is correct to spec. but odd looking.
    """

    def increase_indent(self, flow=False, indentless=False):
        return super(IndentLists, self).increase_indent(flow, False)


def _config(key):
    """Get config from environment or CONFIG module"""
    return os.environ.get(key) or getattr(CONFIG, key, None)


def get_base_port():
    """Base port for host port usage"""
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
    """Run a git command"""
    if isinstance(cmd, list):
        cmd = " ".join(cmd)
    if cmd.startswith("clone "):
        cmd = f"git {cmd}"
    else:
        # don't assume git is new enough to support -C path
        cmd = f"cd {repo}; git {cmd}"
    print(cmd)
    subprocess.Popen(cmd, shell=True).communicate()


def get_repos():
    """Check repos are here, clone if not."""
    auth = _config("GIT_USER")
    token = _config("GIT_TOKEN")
    if auth is not None and token is not None:
        auth = f"{auth}:{token}"
    for repo in TEST_BRANCH:
        if not Path(repo).exists():
            git(
                repo,
                [
                    "clone",
                    _config("GIT_BASE_URL").format(auth=auth or "") + repo,
                ],
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
        ("config", []),
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
    """External (host) ports - not sure we need all these"""
    base_port = get_base_port()
    ports = [
        'EXT_VUE_APP_PORT',
        'EXT_DJANGO_API_PORT',
        'EXT_DJANGO_ADMIN_PORT',
        'EXT_KETCHER_PORT',
        # 'EXT_MARVIN_PORT',  # can't pull image without auth
    ]

    return {i: base_port + n for n, i in enumerate(ports)}


def get_env():
    """Collect .env vars from sub-projects, then add test deply vars"""
    user = os.environ['USER']
    env = [f"COMPOSE_PROJECT_NAME={user}_CR"]
    for path in DOCKER_REPOS:
        env.extend(["", "#" * 60, f"# template.env from {path}", "#" * 60, ""])
        env.extend([i.rstrip('\n') for i in open(f"{path}/template.env")])

    env.extend(["", "#" * 60, "# chemcurator_test settings", "#" * 60, ""])
    # exposed ports
    exposed = [f"{k}={v}" for k, v in get_exposed_ports().items()]
    env.extend(exposed)
    print('\n'.join(exposed))
    # API as seen from browser
    env.append("VUE_APP_API_URL=http://localhost:${EXT_DJANGO_API_PORT}")
    env.append("VUE_APP_KETCHER_URL=http://localhost:${EXT_KETCHER_PORT}")
    # not without license
    # env.append("VUE_APP_MARVIN_URL=http://localhost:${EXT_MARVIN_PORT}")
    # Resolver, as seen from API container
    env.append("RESOLUTION_URL=http://web:5000")

    secret = lambda: sha256(str(env).encode('utf8')).hexdigest()
    env.append(f"ADMIN_SECRET_KEY={secret()}")
    env.append(f"API_SECRET_KEY={secret()}")
    env.append(f"SECRET_KEY={secret()}")
    return env


def dict_merge(a, b, path=None):
    """merges b into a
    https://stackoverflow.com/a/7205107/1072212
    """
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                print(f"{key}: {b[key]} overwrites {a[key]}")
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def get_docker_compose():

    user = os.environ['USER']
    # load and heavily edit docker-compose.ymls
    dc = {
        'services': {
            # Not included in django / resolver compositions, this is the
            # main DB, resolver has it's own.
            'postgresql': {
                'image': "postgres:12-alpine",
                'volumes': [
                    f"{user}_chemreg_postgres_data:/var/lib/postgresql/data/",
                ],
                'environment': {
                    'POSTGRES_USER': "${SQL_USER}",
                    'POSTGRES_PASSWORD': "${SQL_PASSWORD}",
                    'POSTGRES_DB': "${SQL_DATABASE}",
                },
            }
        },
    }

    for dcy in (
        'resolver/docker-compose.yml',
        'chemcurator_django/docker-compose.yaml',
    ):
        dict_merge(dc, yaml.safe_load(open(dcy)))

    # replace ports, make context / volume paths relative to here
    dc['services']['web'].pop('ports', None)
    dc['services']['web']['build'] = {"context": "./resolver/"}
    dc['services']['web']['volumes'] = [
        "./resolver/migrations:/code/migrations",
        "./resolver/resolver:/code/resolver",
    ]
    # replace ports, make volume name user specific
    dc['services']['db'].pop('ports', None)
    dc['services']['db']['volumes'] = [
        f"{user}_resolver_postgres_data:/var/lib/postgresql/data/"
    ]

    # update chemcurator_django services
    dc['services']['chemreg-admin']['build'][
        'context'
    ] = './chemcurator_django/'
    dc['services']['chemreg-api']['build']['context'] = './chemcurator_django/'
    dc['services']['chemreg-admin']['ports'] = [
        "${EXT_DJANGO_ADMIN_PORT}:8000"
    ]
    dc['services']['chemreg-api']['ports'] = ["${EXT_DJANGO_API_PORT}:8000"]

    # add chemcurator_vuejs service
    dc['services']['chemreg-ui'] = {
        'build': {'context': 'chemcurator_vuejs'},
        'env_file': [".env"],
        'ports': ["${EXT_VUE_APP_PORT}:8080"],
        'command': ["npm", "run", "serve"],
    }

    # add ketcher service
    dc['services']['chemreg-ketcher'] = {
        'build': {'context': 'chemcurator_vuejs/ketcher'},
        'env_file': [".env"],
        'ports': ["${EXT_KETCHER_PORT}:8002"],
    }
    # doesn't work because it's licensed software, image pull requires auth
    # # add marvin service
    # dc['services']['chemreg-marvin'] = {
    #     'build': {'context': 'chemcurator_vuejs/marvin'},
    #     'env_file': [".env"],
    #     'ports': ["${EXT_MARVIN_PORT}:80"],
    # }

    for service in dc['services']:
        dc['services'][service].pop('restart', None)
        # don't name the service this way, we want the COMPOSE_PROJECT_NAME
        # mechanism to make it user unique
        if 'build' in dc['services'][service]:
            dc['services'][service].pop('image', None)

    for service in dc['services']:
        # disable services, currently no services are disabled
        if service not in (
            'chemreg-admin',
            'chemreg-api',
            'chemreg-ketcher',
            'chemreg-marvin',
            'chemreg-ui',
            'db',  # resolver DB
            'pgbouncer',
            'postgresql',  # chemreg DB
            'redis',
            'web',  # resolver
        ):
            print(f"Deactivating {service}")
            dc['services'][service]['entrypoint'] = 'date'
            dc['services'][service]['command'] = ''

    # deliberately replace any merged volumes section
    dc['volumes'] = {
        f"{user}_chemreg_postgres_data": None,
        f"{user}_resolver_postgres_data": None,
    }
    return dc


def cmd_list(opt):
    for repo in TEST_BRANCH:
        git(repo, ("branch -a"))


def cmd_co(opt):
    git(opt.repo, (f"checkout {opt.branch}"))


def cmd_build(opt):
    pass
    # old_cd = os.getcwd()


def cmd_config(opt):
    with open('.env', 'w') as out:
        ts = time.asctime()
        out.write(f"# AUTOMATICALLY GENERATED {ts}\n")
        out.write("# DO NOT EDIT\n\n")
        out.write('\n'.join(get_env()))
    with open('docker-compose.yml', 'w') as out:
        ts = time.asctime()
        out.write(f"# AUTOMATICALLY GENERATED {ts}\n")
        out.write("# DO NOT EDIT\n\n")
        out.write(
            yaml.dump(get_docker_compose(), indent=4, Dumper=IndentLists)
        )
    print(".env and docker-compose.yml written, run:")
    print("docker-compose config")


def cmd_down(opt):
    pass


def main():
    opt = get_options()
    get_repos()
    opt.func(opt)


if __name__ == "__main__":
    main()
