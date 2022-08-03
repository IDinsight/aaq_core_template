resource "random_password" "db_password" {
  length = 12
  special = false
}

resource "aws_security_group" "db_security_group" {
    vpc_id       = var.vpc_id
    name         = "${var.project_name}-db-sg"
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-db-sg"
        Project = var.project_name
    }
}

# Allow all incoming requests on port 5432 for db security group
resource "aws_security_group_rule" "ingress_5432" {
    type = "ingress"
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_group_id = aws_security_group.db_security_group.id
} 


resource "aws_db_instance" "db" {
    allocated_storage           = 100
    storage_type                = "gp2"
    engine                      = "postgres"
    engine_version              = "12.8"
    instance_class              = var.db_instance_type
    db_subnet_group_name        = var.aws_db_subnet_group_name
    backup_retention_period     = 7
    identifier                  = var.project_name
    db_name                     = var.db_name
    final_snapshot_identifier   = "${var.project_name}-final-snapshot"
    storage_encrypted           = true
    vpc_security_group_ids      = [aws_security_group.db_security_group.id]
    username                    = var.db_username
    password                    = random_password.db_password.result
    port                        = 5432
    publicly_accessible         = true
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-db-server"
        Project = var.project_name
    }
}

resource "aws_secretsmanager_secret" "db_secret" {
  name = "${var.project_name}-db"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-db-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_secret" {
  secret_id     = aws_secretsmanager_secret.db_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.db.address, "db_username": var.db_username, "db_password": random_password.db_password.result})
}
