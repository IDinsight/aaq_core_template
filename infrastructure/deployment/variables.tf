variable "project_name" {
  type = string

  validation {
    condition     = var.project_name != "<fill_project_name>"
    error_message = "You must provide your project name in deployment.auto.tfvars."
  }

 validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.project_name))
    error_message = "Invalid project name. Project names must be all lowercase letters with non-consecutive hyphens, e.g. my-airflow-project."
  }
}

variable "billing_code" {
  type = string

  validation {
    condition     = var.billing_code != "<fill_billing_code>"
    error_message = "You must provide your billing code in deployment.auto.tfvars."
  }
}

variable "region" {
  type = string
  
  validation {
    condition     = var.region != "<fill_aws_region>"
    error_message = "You must provide your AWS region in deployment.auto.tfvars."
  }
}

variable "keypair_name" {
  type = string
  validation {
    condition     = var.keypair_name != "<fill_keypair_name>"
    error_message = "You must provide your keypair name in deployment.auto.tfvars."
  }
}

variable "ec2_instance_type" {
    type = string
    default = "r5.large"
}

variable "db_instance_type" {
    type = string
    default = "db.t3.medium"
}

variable "db_username" {
    type = string
    default = "admin_user"
}

variable "aws_profile_name" {
    type = string
    default = "default"
}