resource "random_password" "admin_password" {
  length = 12
  special = false
}

resource "random_password" "dev_password" {
  length = 12
  special = false
}

resource "random_password" "test_password" {
  length = 12
  special = false
}

variable "db_username" {
  type = string
  default = "admin_user"
}

variable "dev_user" {
  type = string
  default = "flask"
}

variable "test_user" {
  type = string
  default = "flask_test"
}

resource "aws_security_group" "db_security_group" {
    vpc_id       = var.vpc_id
    name         = "${var.project_name}-dev-db-sg"
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-dev-db-sg"
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
    identifier                  = "${var.project_name}-dev"
    final_snapshot_identifier   = "${var.project_name}-dev-final-snapshot"
    storage_encrypted           = true
    vpc_security_group_ids      = [aws_security_group.db_security_group.id]
    username                    = var.db_username
    password                    = random_password.admin_password.result
    port                        = 5432
    publicly_accessible         = true
    skip_final_snapshot         = true
    tags = {
        BillingCode = var.billing_code
        Name = "${var.project_name}-dev-db-server"
        Project = var.project_name
    }
}

resource "null_resource" "db_setup" {

  # runs after database and security group providing external access is created
  depends_on = [aws_db_instance.db, aws_security_group.db_security_group]

    provisioner "local-exec" {
      command = "psql -v u1=\"${var.dev_user}\" -v p1=\"'${random_password.dev_password.result}'\" -v d1=\"${var.project_name}_dev\" -v u2=\"${var.test_user}\" -v p2=\"'${random_password.test_password.result}'\" -v d2=\"${var.project_name}_test\" -h \"${aws_db_instance.db.address}\" -p ${aws_db_instance.db.port} -U \"${var.db_username}\" -d \"postgres\" -f \"${path.module}/db_init.sql\" "
      
      environment = {
        PGPASSWORD = random_password.admin_password.result
      }
    }
}

resource "aws_secretsmanager_secret" "db_secret" {
  name = "${var.project_name}-dev-db"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-dev-db-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_secret" {
  secret_id     = aws_secretsmanager_secret.db_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.db.address, "db_username": var.db_username, "db_password": random_password.admin_password.result})
}


resource "aws_secretsmanager_secret" "flask_dev_secret" {
  name = "${var.project_name}-db-flask-dev"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-db-flask-dev-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "flask_dev_secret" {
  secret_id     = aws_secretsmanager_secret.flask_dev_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.db.address, "db_username": var.dev_user, "db_password": random_password.dev_password.result})
}

resource "aws_secretsmanager_secret" "flask_test_secret" {
  name = "${var.project_name}-db-flask-test"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-db-flask-test-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "flask_test_secret" {
  secret_id     = aws_secretsmanager_secret.flask_test_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.db.address, "db_username": var.test_user, "db_password": random_password.test_password.result})
}
