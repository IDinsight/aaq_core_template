# Testing setup

Some of the test cases need access to database. 
!!! DO NOT USE THE DEV DATABASE !!!

The fixtures in the test delete all rows in the tables after the test has been run. So ensure you are using the testing db - `pytest_praekelt_dev`.

## Setup database connection

1. Create a new file called `db_secrets.env` in this directory (`\tests\`).
2. Add the following details to the file
```shell
PG_ENDPOINT=<DB_ENDPOINT>
PG_PORT=5432
PG_DATABASE=praekeltmcpytestdb
PG_USERNAME=flask
PG_PASSWORD=<DB_PASSWORD>
```

Secrets are stored in Dashlane. Reach out to Sid, Victor, or Suzin to get the values.

!!! DO NOT USE THE DEV DATABASE !!!

## Running tests

From the root of the folder, run either `make test` for `make test-all` . Note that `make test-all` also runs the slow tests, usually because it has to load up the pretrained model.


