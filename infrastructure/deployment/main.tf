terraform {
  backend "s3" {
  }
}

module "deployment" {
    source = "../tf_module"

    project_name = var.project_name
    billing_code = var.billing_code
    region = var.region
    keypair_name = var.keypair_name

    dev_ec2_instance_type = var.dev_ec2_instance_type
    dev_db_instance_type = var.dev_db_instance_type
    ec2_instance_type = var.ec2_instance_type
    db_instance_type = var.db_instance_type
    
    aws_profile_name = var.aws_profile_name
}