# Steps for setting up the AWS infrastructure

## 1. Set up terraform backend

1. Update `project_config.cfg` with required variables.
    - Make sure to choose a value for `PROJECT_SHORT_NAME` that contains only lowercase letters and hyphens (e.g.
      my-project).
    - Make sure that `AWS_PROFILE_NAME` is the name of the profile (stored in `~/.aws/credentials`) with appropriate
      permissions to create and destroy AWS resources.
2. Check the input variable definition file `infrastructure/tf_backend/variables.tf` for other input variables that you
   may want to override the default values for.
3. Run the following command:`make tf-backend-apply`. Only confirm by typing 'yes' if the changes being made are as
   expected.
   <br/>
   This sets up the S3 bucket and dynamodb table which will be used to store terraform metadata for the project.

## 2. Deploy dev/test components

1. On the AWS console, create an ssh keypair called `<PROJECT_SHORT_NAME>-keypair` in the same region where you will
   deploy. You can find the keypair creation screen under EC2 > Key Pairs (on the left-hand menu under "Network &
   Security"). Save the private key (the .pem file) in your local `~/.ssh/` directory.
2. Check the input variable definition file `infrastructure/deployment/variables.tf` for input variables that you may
   want to override the default values for.
3. Run the following command:`make tf-apply`. Only confirm by typing 'yes' if the changes being made are as expected.

This sets up all the AWS components needed:

1. VPC, subnets and security groups
2. EC2, RDS with development and testing database and secrets with the DB credentials for admin user, flask and
   flask_test user
3. EC2, RDS and ECS cluster for staging environment To add/remove any resources, update the code
   in `infrastructure/tf_module` before deployment.
4. Github Actions user for staging deployment with all required permissions

# Additional things to note

## 1. To remove the resources

To remove the resources created by terraform run `make tf-destroy`.

This first remove the project resources by running `terraform destroy` and then permanently deletes the secrets using
the python script `infrastructure/delete_secrets.py` because `terraform destroy` only schedules secrets to be deleted.

## 2. To removes the Terraform backend

To removes the Terraform backend as well run `make tf-backend-destroy`

## 3. To connect to the PostgreSQL database

To connect to the PostgreSQL database created as part of deployment, obtain the database credentials (host, username and
password) from the secrets

- staging admin user: `<PROJECT_SHORT_NAME>-db`
- dev admin user: `<PROJECT_SHORT_NAME>-dev-db`
- dev flask user: `<PROJECT_SHORT_NAME>-db-flask-dev`
- dev flast_test user`<PROJECT_SHORT_NAME>-db-flask-test`

## 4. To obtain Github Actions user credentials

Github Actions user credentials are stored in a secret called `<PROJECT_SHORT_NAME>-staging-ga-user-credentials`.

## 5. To run Github Actions

### 5.1 Update your Github Actions secrets

In the environment `staging`,

- Create or update AWS secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` with the values saved
  in `<PROJECT_SHORT_NAME>-staging-ga-user-credentials` in AWS Secrets Manager.
- Create or update the DB secrets: `GA_PG_ENDPOINT` and `GA_PG_PASSWORD` with AWS secret `<PROJECT_SHORT_NAME>-db`.

In the repository environment  (assuming only test DB will be used)

- Create or update the DB secrets: `GA_PG_ENDPOINT` and `GA_PG_PASSWORD` with AWS
  secret `<PROJECT_SHORT_NAME>-db-flask-test`.

### 5.2 Update your tests config

Update the databse configs in pytests.

In both `tests/configs/base.yaml` and `validation/config.yaml`, change the value stored in `PG_DATABASE`
to `<PROJECT_SHORT_NAME>_test`.
