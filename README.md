# chemcurator_test

(Experimental) test environment for ChemReg / ChemCurator

Assumes the `chemcurator_django`, `chemcurator_vuejs`, and `resolver` repos.
can be clone with the info. in chemcurator_test_config.py.

Copy chemcurator_test_config.py.template to chemcurator_test_config.py
and edit appropriately.  For simplicity you can use a dedicated GitHub access
token, so {auth} is replaced with <githubuser>:<accesstoken>.
chemcurator_test_config.py should not be shared or committed to version
control.  BASE_PORT can be any port number, 9000 or 39000 or whatever.

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

 - add ketcher
 - revisit chemcurator_test.py subcommands for managing branches for testing
 etc.

### chemcurator_vuejs notes

Currently the test deployment code makes no changes to the component repos.  So
the chemcurator_vuejs Dockerfile builds static production assets.  But the
chemcurator_test docker-compose overwrites the CMD to "npm run serve", so the
container runs in dev. mode.

The static production assets do not seem to use the right API URL, i.e. not
reading VUE_APP_API_URL correctly, but it works in dev. mode.
