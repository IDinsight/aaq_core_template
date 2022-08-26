# Testing setup

Some of the test cases need access to database. 
!!! DO NOT USE THE DEV DATABASE !!!

The fixtures in the test delete all rows in the tables after the test has been run. So ensure you are using the testing db.

## Setup database connection

Update details your wish to override in the `yaml` files under `configs`. 
You may wish to add it to .gitignore if it will include passwords.

## Running tests

From the root of the folder, run either `make test` for `make test-all`.
Note that `make test-all` also runs the slow tests, usually because it has to load up the pretrained model.
