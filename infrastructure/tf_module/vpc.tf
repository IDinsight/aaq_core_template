# Part 1: VPC

module "vpc" {
    source  = "terraform-aws-modules/vpc/aws"
    version = "2.77.0"

    name = "${var.project_name}-vpc"

    cidr           = "20.10.0.0/16"
    enable_dns_support   = true
    enable_dns_hostnames = true

    # Cloudwatch log group and IAM role will be created
    enable_flow_log                      = true
    create_flow_log_cloudwatch_log_group = true
    create_flow_log_cloudwatch_iam_role  = true
    flow_log_max_aggregation_interval    = 60

    vpc_flow_log_tags = {
        Name = "${var.project_name}-vpc-flow-logs"
        Project = var.project_name
        BillingCode = var.billing_code
    }

    tags = {
        Name = "${var.project_name}-vpc"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "public_subnet_1" {
    vpc_id                  = module.vpc.vpc_id
    cidr_block              = "20.10.11.0/24"
    availability_zone       = data.aws_availability_zones.available.names[0]
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.project_name}-public-subnet-1"
        Type = "public"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_subnet" "public_subnet_2" {
    vpc_id                  = module.vpc.vpc_id
    cidr_block              = "20.10.12.0/24"
    availability_zone       = data.aws_availability_zones.available.names[1]
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.project_name}-public-subnet-2"
        Type = "public"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_subnet" "db_subnet_1" {
    vpc_id                  = module.vpc.vpc_id
    cidr_block              = "20.10.21.0/24"
    availability_zone       = data.aws_availability_zones.available.names[0]
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.project_name}-db-subnet-1"
        Type = "db"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_subnet" "db_subnet_2" {
    vpc_id                  = module.vpc.vpc_id
    cidr_block              = "20.10.22.0/24"
    availability_zone       = data.aws_availability_zones.available.names[1]
    map_public_ip_on_launch = true
    tags = {
        Name = "${var.project_name}-db-subnet-2"
        Type = "db"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_db_subnet_group" "default" {
    name       = "${var.project_name}_db_subnet_group"
    subnet_ids = [aws_subnet.db_subnet_1.id, aws_subnet.db_subnet_2.id]
    tags = {
        Name = "${var.project_name}-db-subnet-group"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_internet_gateway" "default" {
    vpc_id = module.vpc.vpc_id
    tags = {
        Name = "${var.project_name}-internet-gateway"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_route_table" "public_route_table" {
    vpc_id = module.vpc.vpc_id
    tags = {
        Name = "${var.project_name}-public-route-table"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_route_table" "db_route_table" {
    vpc_id = module.vpc.vpc_id
    tags = {
        Name = "${var.project_name}-db-route-table"
        Project = var.project_name
        BillingCode = var.billing_code
    }
}

resource "aws_route" "public_route_1" {
    route_table_id         = aws_route_table.public_route_table.id
    destination_cidr_block = "0.0.0.0/0"
    gateway_id             = aws_internet_gateway.default.id
}

resource "aws_route" "db_route_1" {
    route_table_id         = aws_route_table.db_route_table.id
    destination_cidr_block = "0.0.0.0/0"
    gateway_id             = aws_internet_gateway.default.id
}

resource "aws_route_table_association" "route_table_assocation_public_subnet_1" {
    subnet_id      = aws_subnet.public_subnet_1.id
    route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "route_table_assocation_public_subnet_2" {
    subnet_id      = aws_subnet.public_subnet_2.id
    route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table_association" "route_table_assocation_db_subnet_1" {
    subnet_id      = aws_subnet.db_subnet_1.id
    route_table_id = aws_route_table.db_route_table.id
}

resource "aws_route_table_association" "route_table_assocation_db_subnet_2" {
    subnet_id      = aws_subnet.db_subnet_2.id
    route_table_id = aws_route_table.db_route_table.id
}
