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

data "aws_caller_identity" "current" {}

# Get EC2 Amazon ECS-optimized AMI
data "aws_ami" "amazon_linux_2" {

    owners = ["amazon"]

    filter {
        name   = "owner-alias"
        values = ["amazon"]
    }

    filter {
        name   = "name"
        values = ["amzn2-ami-ecs-hvm*"]
    }

    filter {
        name   = "name"
        values = ["*x86_64*"]
    }
    most_recent = true

}

# Get the EC2 instance user data for ECS connection
data "template_file" "user_data" {
  template = file("${path.module}/bootstrap.tpl")
  vars = {
    account_id = data.aws_caller_identity.current.account_id
  }
}

# Security group for the EC2 instance
resource "aws_security_group" "ec2_security_group" {
    vpc_id       = var.vpc_id
    name         = "${var.project_name}-dev-ec2-sg"
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-ec2-sg"
        Project = var.project_name
    }
}

# Allow EC2 instance to use ports 9000, 9902, 9903, 9904 for internal requests
resource "aws_security_group_rule" "ingress_9000" {
    type = "ingress"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 9000
    to_port     = 9000
    protocol    = "tcp"
    security_group_id = aws_security_group.ec2_security_group.id
} 

resource "aws_security_group_rule" "ingress_990n" {
    type = "ingress"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 9902
    to_port     = 9904
    protocol    = "tcp"
    security_group_id = aws_security_group.ec2_security_group.id
} 


# Allow EC2 instance to use SSH for internal requests
resource "aws_security_group_rule" "ingress_22" {
    type = "ingress"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    security_group_id = aws_security_group.ec2_security_group.id
} 

# Allow EC2 instance to use all outbound traffic - need to change?
resource "aws_security_group_rule" "egress_all" {
    type = "egress"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 0
    protocol    = "all"
    security_group_id = aws_security_group.ec2_security_group.id
} 

# Create the EC2 instance
resource "aws_instance" "ec2_server" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = var.ec2_instance_type
  vpc_security_group_ids      = [aws_security_group.ec2_security_group.id]
  subnet_id                   = var.public_subnet_id
  key_name                    = var.keypair_name
  user_data                   = base64encode(data.template_file.user_data.rendered)
  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-dev-server"
    Project = var.project_name
  }
  lifecycle {
    ignore_changes = [
        ami
    ]
  }
}
