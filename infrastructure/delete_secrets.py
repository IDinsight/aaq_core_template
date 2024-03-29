import sys

import boto3
from botocore.config import Config

project_name = sys.argv[1]
region_name = sys.argv[2]

client = boto3.client("secretsmanager", config=Config(region_name=region_name))

client.delete_secret(SecretId=f"{project_name}-db", ForceDeleteWithoutRecovery=True)

client.delete_secret(SecretId=f"{project_name}-dev-db", ForceDeleteWithoutRecovery=True)

client.delete_secret(
    SecretId=f"{project_name}-db-flask-dev", ForceDeleteWithoutRecovery=True
)

client.delete_secret(
    SecretId=f"{project_name}-db-flask-test", ForceDeleteWithoutRecovery=True
)

client.delete_secret(
    SecretId=f"{project_name}-staging-ga-user-credentials", ForceDeleteWithoutRecovery=True
)
