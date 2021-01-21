# chemcurator_test

(Experimental) test environment for ChemReg / ChemCurator

Assumes the `chemcurator_django`, `chemcurator_vuejs`, and `resolver` repos.
can be clone with the info. in chemcurator_test_config.py.

Copy chemcurator_test_config.py.template to chemcurator_test_config.py
and edit appropriately.  For simplicity you can use a dedicated GitHub access
token, so {auth} is replaced with `<githubuser>:<accesstoken>`.
chemcurator_test_config.py should not be shared or committed to version
control.  BASE_PORT can be any port number, 9000 or 39000 or whatever.

`chemcurator_test.py` is a "bash script" written in Python which merges the
docker-compose.yml and template.env files for chemcurator_django and resolver
and adds entries for chemcurator_vuejs.  It may handle branch management for
testing later, but for now it's basically just merging.  You provide a base
port number X in chemcurator_test_config.py and the code assigns X, X+1, etc.
as required as host ports exposing container ports.

Assuming you have Python 3
```shell
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python chemcurator_test.py --help
python chemcurator_test.py config
docker-compose build
docker-compose up
```

The following containers are launched by default:
```
web             <- resolver
chemreg-admin   30006->8000
chemreg-api     30005->8000
db              <- resolver
chemreg-ketcher 30007->8002
postgresql      <- ChemReg DB
redis
chemreg-cypress 30008->22, 30009->8080
chemreg-ui      30004->8080
pgbouncer   
```
`<username>_cr_` is prepended to images / containers to avoid conflicts with
other users.

The `chemreg-cypress` is only for testing.

## (Currently) manual steps

After bringing everything up,
```shell
docker-compose exec chemreg-api bash
python manage.py migrate
# compounds < substances < lists order matters
python manage.py loaddata chemreg/fixtures/users.yaml
python manage.py loaddata chemreg/fixtures/compounds.yaml
python manage.py loaddata chemreg/fixtures/substances.yaml
python manage.py loaddata chemreg/fixtures/lists.yaml
```
these changes should persist until the persistent DB volume is destroyed, so
not needed often.

## Working

chemcurator_test.py builds a usable .env and docker-compose.yml for deploying
all ChemReg components in a single docker network.

## To do

 [x] add ketcher
 [ ] revisit chemcurator_test.py subcommands for managing branches for testing
     etc.

### chemcurator_vuejs notes

Currently the test deployment code makes no changes to the component repos.  So
the chemcurator_vuejs Dockerfile builds static production assets.  But the
chemcurator_test docker-compose overwrites the CMD to "npm run serve", so the
container runs in dev. mode.

The static production assets do not seem to use the right API URL, i.e. not
reading VUE_APP_API_URL correctly, but it works in dev. mode.
