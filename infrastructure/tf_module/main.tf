terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
    postgresql = {
      source = "cyrilgdn/postgresql"
      version = ">=1.15.0"
    }
  }
}

provider "aws" {
    region = var.region
    profile = "${var.aws_profile_name}"
}

module "common" {
  source = "./common"

  project_name = var.project_name
  billing_code = var.billing_code
  region = var.region
  aws_profile_name = var.aws_profile_name
}

module "dev" {
  source = "./dev"
  
  vpc_id = module.common.vpc_id
  aws_db_subnet_group_name = module.common.aws_db_subnet_group_name
  public_subnet_id = module.common.public_subnet_id

  project_name = var.project_name
  billing_code = var.billing_code
  region = var.region
  keypair_name = var.keypair_name
  ec2_instance_type = var.dev_ec2_instance_type
  db_instance_type = var.dev_db_instance_type
  aws_profile_name = var.aws_profile_name
}

module "stg" {
  source = "./stg"
  
  vpc_id = module.common.vpc_id
  aws_db_subnet_group_name = module.common.aws_db_subnet_group_name
  public_subnet_id = module.common.public_subnet_id

  project_name = var.project_name
  billing_code = var.billing_code
  region = var.region
  keypair_name = var.keypair_name
  ec2_instance_type = var.ec2_instance_type
  db_instance_type = var.db_instance_type
  aws_profile_name = var.aws_profile_name

  db_name = var.project_name
  db_username = "flask"
}

