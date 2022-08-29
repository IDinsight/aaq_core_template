variable "project_short_name" {
  type = string

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.project_short_name))
    error_message = "Invalid project name. Project names must be all lowercase letters with non-consecutive hyphens, e.g. my-airflow-project."
  }
}

variable "billing_code" {
  type = string

  validation {
    condition     = var.billing_code != ""
    error_message = "You must provide your billing code."
  }
}

variable "region" {
  type = string
  
  validation {
    condition     = var.region != ""
    error_message = "You must provide your AWS region."
  }
}

variable "keypair_name" {
  type = string
  validation {
    condition     = var.keypair_name != ""
    error_message = "You must provide your keypair name."
  }
}

variable "dev_ec2_instance_type" {
    type = string
    default = "r5.large"
}

variable "dev_db_instance_type" {
    type = string
    default = "db.t3.medium"
}

variable "ec2_instance_type" {
    type = string
    default = "r5.large"
}

variable "db_instance_type" {
    type = string
    default = "db.t3.medium"
}

variable "aws_profile_name" {
    type = string
    default = "default"
}