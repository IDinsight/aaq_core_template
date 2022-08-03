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
    cluster_name = aws_ecs_cluster.ecs_cluster.name
  }
}

# Security group for the EC2 instance
resource "aws_security_group" "ec2_security_group" {
    vpc_id       = var.vpc_id
    name         = "${var.project_name}-ec2-sg"
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

# Create a EC2 instance profile
resource "aws_iam_instance_profile" "instance_profile" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.instance_role.name
}

# Create the EC2 instance
resource "aws_instance" "ec2_server" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = var.ec2_instance_type
  vpc_security_group_ids      = [aws_security_group.ec2_security_group.id]
  subnet_id                   = var.public_subnet_id
  iam_instance_profile        = aws_iam_instance_profile.instance_profile.name
  key_name                    = var.keypair_name
  user_data                   = base64encode(data.template_file.user_data.rendered)
  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-server"
    Project = var.project_name
  }
  lifecycle {
    ignore_changes = [
        ami
    ]
  }
}

resource "aws_ecs_cluster" "ecs_cluster" {
    name  = "${var.project_name}-cluster"
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-cluster"
        Project = var.project_name
    }
}

data "aws_iam_policy_document" "agent_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# Create an IAM role for ECS EC2
resource "aws_iam_role" "instance_role" {
    name = "${var.project_name}-instance-role"
    assume_role_policy = data.aws_iam_policy_document.agent_assume_role.json

    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-instance-role"
        Project = var.project_name
    }
}

# Standard EC2 ECS agent
resource "aws_iam_role_policy_attachment" "ecs_agent_ec2" {
  role       = aws_iam_role.instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

# Task execution role for ECS
resource "aws_iam_role" "task_role" {
  name = "${var.project_name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        "Sid" : "",
        "Effect" : "Allow",
        "Principal" : {
          "Service" : "ecs-tasks.amazonaws.com"
        },
        "Action" : "sts:AssumeRole"
      },
    ]
  })

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-task-role"
    Project = var.project_name
  }
}

# Create a policy for the EC2 role to use Session Manager, ECR, and Secrets Manager
resource "aws_iam_role_policy" "ec2_role_policy" {
  name = "${var.project_name}-ec2-role-policy"
  role = aws_iam_role.task_role.id
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement":
    [
        {
            "Effect": "Allow",
            "Action":
            [
                "ssm:DescribeAssociation",
                "ssm:GetDeployablePatchSnapshotForInstance",
                "ssm:GetDocument",
                "ssm:DescribeDocument",
                "ssm:GetManifest",
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:ListAssociations",
                "ssm:ListInstanceAssociations",
                "ssm:PutInventory",
                "ssm:PutComplianceItems",
                "ssm:PutConfigurePackageResult",
                "ssm:UpdateAssociationStatus",
                "ssm:UpdateInstanceAssociationStatus",
                "ssm:UpdateInstanceInformation"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action":
            [
                "ssmmessages:CreateControlChannel",
                "ssmmessages:CreateDataChannel",
                "ssmmessages:OpenControlChannel",
                "ssmmessages:OpenDataChannel"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action":
            [
                "ec2messages:AcknowledgeMessage",
                "ec2messages:DeleteMessage",
                "ec2messages:FailMessage",
                "ec2messages:GetEndpoint",
                "ec2messages:GetMessages",
                "ec2messages:SendReply"
            ],
            "Resource": "*"
        },
        {
            "Sid": "secretsPermissions",
            "Effect": "Allow",
            "Action":
            [
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds"
            ],
            "Resource":
            [
                "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}-*"
            ]
        },
        {
            "Sid": "secretsManagerPermissions",
            "Effect": "Allow",
            "Action":
            [
                "secretsmanager:GetRandomPassword",
                "secretsmanager:ListSecrets"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ecrAccess",
            "Effect": "Allow",
            "Action":
            [
                "ecr:*",
                "cloudtrail:LookupEvents"
            ],
            "Resource": "*"
        }
    ]
}
  EOF
}