resource "random_password" "db_password" {
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

resource "aws_security_group" "db_security_group" {
    vpc_id       = module.vpc.vpc_id
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


resource "aws_db_instance" "default" {
    allocated_storage           = 100
    storage_type                = "gp2"
    engine                      = "postgres"
    engine_version              = "12.8"
    instance_class              = var.db_instance_type
    db_subnet_group_name        = aws_db_subnet_group.default.name
    backup_retention_period     = 7
    identifier                  = var.project_name
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
  secret_string = jsonencode({"db_endpoint": aws_db_instance.default.address, "db_username": var.db_username, "db_password": random_password.db_password.result})
}


provider "postgresql" {
  host             = aws_db_instance.default.address
  port             = aws_db_instance.default.port
  username         = aws_db_instance.default.username
  password         = random_password.db_password.result
  expected_version = aws_db_instance.default.engine_version
  sslmode          = "require"
  superuser        = false
}

# Create flask_dev User
resource "postgresql_role" "dev_db_role" {
    name                = "flask_dev"
    login               = true
    password            = random_password.dev_password.result
    encrypted_password  = true
    depends_on          = [aws_db_instance.default]
}
# Create dev database 
resource "postgresql_database" "dev_db" {
    name              = "development"
    owner             = "flask_dev"
    depends_on        = [postgresql_role.dev_db_role]
}

resource "aws_secretsmanager_secret" "db_dev_secret" {
  name = "${var.project_name}-db-flask-dev"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-db-flask-dev-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_dev_secret" {
  secret_id     = aws_secretsmanager_secret.db_dev_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.default.address, "db_username": postgresql_role.dev_db_role.name, "db_password": random_password.dev_password.result})
}


# Create flask_test user
resource "postgresql_role" "test_db_role" {
    name                = "flask_test"
    login               = true
    password            = random_password.test_password.result
    encrypted_password  = true
    depends_on          = [aws_db_instance.default]
}

# Create test database 
resource "postgresql_database" "test_db" {
    name              = "test"
    owner             = "flask_test"
    depends_on        = [postgresql_role.test_db_role]
}

resource "aws_secretsmanager_secret" "db_test_secret" {
  name = "${var.project_name}-db-flask-test"

  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-db-flask-test-secret"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_test_secret" {
  secret_id     = aws_secretsmanager_secret.db_test_secret.id
  secret_string = jsonencode({"db_endpoint": aws_db_instance.default.address, "db_username": postgresql_role.test_db_role.name, "db_password": random_password.test_password.result})
}