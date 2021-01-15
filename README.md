# chemcurator_test

(Experimental) test environment for ChemReg / ChemCurator

### chemcurator_vuejs notes

Currently the test deployment code makes no changes to the component repos.  So
the chemcurator_vuejs Dockerfile builds static production assets.  But the
chemcurator_test docker-compose overwrites the CMD to "npm run serve", so the
container runs in dev. mode.

The static production assets do not seem to use the right API URL, i.e. not
reading VUE_APP_API_URL correctly, but it works in dev. mode.
