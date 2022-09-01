resource "aws_iam_user" "gh_actions" {
  name = "${var.project_name}-staging-ga-user"
  path = "/"

  tags = {
      BillingCode = var.billing_code
      Name = "${var.project_name}-staging-ga-user"
      Project = var.project_name
  }
}

resource "aws_iam_access_key" "gh_actions" {
  user = aws_iam_user.gh_actions.name
}


resource "aws_iam_policy" "amazon_ecs_deploy_task_definition" {
  name  = "${var.project_name}-ecs-deploy"

  # Reference: https://github.com/aws-actions/amazon-ecs-deploy-task-definition
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ecs:RegisterTaskDefinition",
          "ecs:ListAccountSettings",
          "ecs:CreateService"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"

        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "iam:PassRole"
        ]
        Effect   = "Allow"
        Resource = "${aws_iam_role.task_role.arn}"
      },
      {
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DeleteService"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:ecs:${var.region}:${data.aws_caller_identity.current.account_id}:service/${aws_ecs_cluster.ecs_cluster.name}/*"
      },
    ]
  })
}


resource "aws_iam_policy" "amazon_ecr_login" {
  name  = "${var.project_name}-ecr-login"

  # Reference: https://github.com/aws-actions/amazon-ecr-login
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Effect   = "Allow"
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_policy" "amazon_docker_pushpull_permission" {
  name  = "${var.project_name}-ecr-permissions"

  # Reference: https://github.com/aws-actions/amazon-ecr-login
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Effect   = "Allow"
        Resource = "*" #Can be restricted to specific image arns
      },
    ]
  })
}

resource "aws_iam_user_policy_attachment" "amazon_ecs_deploy_task_definition" {
  user       = aws_iam_user.gh_actions.name
  policy_arn = aws_iam_policy.amazon_ecs_deploy_task_definition.arn
}

resource "aws_iam_user_policy_attachment" "amazon_ecr_login" {
  user       = aws_iam_user.gh_actions.name
  policy_arn = aws_iam_policy.amazon_ecr_login.arn
}

resource "aws_iam_user_policy_attachment" "amazon_docker_pushpull_permission" {
  user       = aws_iam_user.gh_actions.name
  policy_arn = aws_iam_policy.amazon_docker_pushpull_permission.arn
}

resource "aws_secretsmanager_secret" "gh_actions" {
  description             = "Praekelt GitHub actions pipeline user credentials"
  name                    = "${var.project_name}-staging-ga-user-credentials"
  
  tags = {
    BillingCode = var.billing_code
    Name = "${var.project_name}-staging-ga-user-credentials"
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "gh_actions" {
  secret_id     = aws_secretsmanager_secret.gh_actions.id
  secret_string = jsonencode({ "aws_access_key_id" = aws_iam_access_key.gh_actions.id, "aws_secret_access_key" = aws_iam_access_key.gh_actions.secret })
}