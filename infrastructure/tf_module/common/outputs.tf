output "vpc_id" {
  value = module.vpc.vpc_id
}

output "aws_db_subnet_group_name" {
  value = aws_db_subnet_group.default.name
}

output "public_subnet_id" {
  value = aws_subnet.public_subnet_1.id
}