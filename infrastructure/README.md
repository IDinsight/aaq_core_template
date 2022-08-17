## Steps for setting up the AWS infrastructure
1. Set up terraform backend:
    - Update `infrastructure/tf_backend/tf_backend.auto.tfvars` with required variables. Make sure to choose a value for project_name that contains only lowercase letters and hyphens (e.g. my-project). Check the input variable definition file `infrastructure/tf_backend/variables.tf` for other input variables that you may want to override the default values for. You should override a default value by adding the variable to the `tf_backend.auto.tfvars` file.
	- cd `infrastructure/tf_backend` and run the following commands:
		- `terraform init`
		- `terraform plan`
		- `terraform apply`
	<br/>
   This sets up the S3 bucket and dynamodb table which will be used to store terraform metadata for the project.

2. Deploy dev/test components:
	- On the AWS console, create an ssh keypair in the same region where you will deploy. You can find the keypair creation screen under EC2 > Key Pairs (on the left-hand menu under "Network & Security"). Save the private key (the .pem file) in your local `~/.ssh/` directory and make note of the keypair name so you can add it to the Terraform deployment variables in the next step.
	- Update `infrastructure/deployment/deployment.auto.tfvars` with required variables. Check the input variable definition file `infrastructure/deployment/variables.tf` for other input variables that you may want to override the default values for. You should override a default value by adding the variable to the `deployment.auto.tfvars` file.
	- Update `infrastructure/deployment/main.tf` backend block with the project name and region name. This configuration points to the S3 bucket and dynamodb table created in step 1. 
	- cd `infrastructure/deployment` and run the following cammands:
		- `terraform init`
		- `terraform plan`
		- `terraform apply`
	<br/>
	This sets up all the AWS components needed: 
	1. VPC, subnets and security groups 
	2. EC2, RDS with development and testing database and secrets with the DB credentials for admin user, flask and flask_test user
	2. EC2, RDS and ECS cluster for staging environment
	To add/remove any resources, update the code in `infrastructure/tf_module` before deployment. 


## Additional things to note:
1. Command to remove the resources created by terraform is `terraform destroy`. To tear down all the infrastructure, first remove the project resources by running `terraform destroy` within `infrastructure/deployment`, then remove the Terraform backend resources by running `terraform destroy` within `infrastructure/tf_backend`.

	- Note that `terraform destroy` only schedules secrets to be deleted, which can pose a problem when you are trying to tear everything down and then immediately rebuild it. To immediately delete the secrets for the project resources, use the python script `infrastructure/delete_secrets.py` after running `terraform destroy`.

2. To connect to the PostgreSQL database created as part of deployment:
	- Obtain the database credentials (host, username and password) from the secret called `<project_name>-db`, `<project_name>-db-flask-dev` or `<project_name>-db-flask-test` for admin user, flask_dev or flask_test user logins respectively.

 