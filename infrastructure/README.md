## Steps for setting up the AWS infrastructure
1. Set up terraform backend:
    - Update `project_config.cfg` with required variables. Make sure to choose a value for solution_name that contains only lowercase letters and hyphens (e.g. my-project). 
    - Check the input variable definition file `infrastructure/tf_backend/variables.tf` for other input variables that you may want to override the default values for. 
	- Run the following command:`make tf-backend-apply`. Only confirm by typing 'yes' if the changes being made are as expected.
	<br/>
   This sets up the S3 bucket and dynamodb table which will be used to store terraform metadata for the project.

2. Deploy dev/test components:
	- On the AWS console, create an ssh keypair called `<PROJECT_SHORT_NAME>-keypair` in the same region where you will deploy. You can find the keypair creation screen under EC2 > Key Pairs (on the left-hand menu under "Network & Security"). Save the private key (the .pem file) in your local `~/.ssh/` directory.
	- Check the input variable definition file `infrastructure/deployment/variables.tf` for input variables that you may want to override the default values for. 
	- Run the following command:`make tf-apply`. Only confirm by typing 'yes' if the changes being made are as expected.
	<br/>
	This sets up all the AWS components needed: 
	1. VPC, subnets and security groups 
	2. EC2, RDS with development and testing database and secrets with the DB credentials for admin user, flask and flask_test user
	3. EC2, RDS and ECS cluster for staging environment
	To add/remove any resources, update the code in `infrastructure/tf_module` before deployment. 
	4. Github Actions user for staging deployment with all required permissions


## Additional things to note:
1. To remove the resources created by terraform: run `make tf-destroy`. This first remove the project resources by running `terraform destroy` and then permanently deletes the secrets using the python script `infrastructure/delete_secrets.py` because `terraform destroy` only schedules secrets to be deleted.

2. To removes the Terraform backend as well run `make tf-backend-destroy` 

3. To connect to the PostgreSQL database created as part of deployment:
	- Obtain the database credentials (host, username and password) from the secret called `<project_name>-db`, `<project_name>-db-flask-dev` or `<project_name>-db-flask-test` for admin user, flask_dev or flask_test user logins respectively.

4. Github Actions user credentials are stored in a secret called `<project_name>-staging-ga-user-credentials`.
 