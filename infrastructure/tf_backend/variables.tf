variable "project_short_name" {
  type = string

  validation {
    condition     = can(regex("^[a-z]+(-[a-z]+)*$", var.project_name))
    error_message = "Invalid project name. Project names must be all lowercase letters with non-consecutive hyphens, e.g. my-superset-project."
  }
}

variable "billing_code" {
  type = string

  validation {
    condition     = var.billing_code != "<fill_billing_code>"
    error_message = "You must provide your billing code."
  }
}

variable "region" {
  type = string
  
  validation {
    condition     = var.region != "<fill_region_name>"
    error_message = "You must provide your AWS region."
  }
}

variable "aws_profile_name" {
  type = string
  default = "default"
}
