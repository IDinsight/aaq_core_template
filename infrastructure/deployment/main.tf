terraform {
  backend "s3" {
    bucket         = "<fill_project_name>-terraform-state" # Fill project name
    key            = "terraform.tfstate"
    region         = "<fill_region_name>" # Fill project name

    dynamodb_table = "<fill_project_name>-terraform-state-locks" # Fill project name
    encrypt        = true
  }
}

module "deployment" {
    source = "../tf_module"

    project_name = var.project_name
    billing_code = var.billing_code
    region = var.region
    keypair_name = var.keypair_name
    ec2_instance_type = var.ec2_instance_type
    db_instance_type = var.db_instance_type
    db_username = var.db_username
    aws_profile_name = var.aws_profile_name
}