
# End goal: build a end-to-end deployment workflow for sharding
# Create the function, grant the function bucket access. 

import os
import boto3
import json
import time
from botocore.exceptions import ClientError

def role_exists(role_name):
    iam = boto3.client('iam')
    try:
        iam.get_role(RoleName=role_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            return False
        else:
            print(f"Error checking for IAM role {role_name}: {e}")
            raise e


def create_lambda_execution_role(role_name):
    iam = boto3.client('iam')

    assume_role_policy_document = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {
                    'Service': 'lambda.amazonaws.com'
                },
                'Action': 'sts:AssumeRole'
            }
        ]
    }

    if not role_exists(role_name):
        try:
            response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy_document)
            )

            policy_arn = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            response = iam.attach_role_policy(
                PolicyArn=policy_arn,
                RoleName=role_name
            )
            time.sleep(10)
            return response

        except ClientError as e:
            print(f"Error creating IAM role {role_name}: {e}")
            raise e
    else:
        print(f"Role {role_name} already exists")


def grant_bucket_access(func_name, bucket_name):
    iam_client = boto3.client('iam')
    lambda_client = boto3.client('lambda')

    # Get the IAM role for the Lambda function
    lambda_config = lambda_client.get_function_configuration(FunctionName=func_name)
    role_arn = lambda_config['Role']

    # Extract the role name from the role ARN
    role_name = role_arn.split('/')[-1]

    # Define the S3 policy JSON
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}/*",
                ]
            }
        ]
    }

    # Create the S3 policy
    try:
        policy_name = f'LambdaS3AccessPolicy-{bucket_name}'
        response = iam_client.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(s3_policy)
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"Policy name 'LambdaS3AccessPolicy-{bucket_name}' exists")

            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']

            response = iam_client.get_policy(
                PolicyArn=f"arn:aws:iam::{account_id}:policy/{policy_name}"
            )
        else:
            raise

    policy_arn = response['Policy']['Arn']
    # Attach the S3 policy to the Lambda IAM role
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_arn
    )

    print(f"Attached policy {policy_name} to role {role_name}")


def deploy_lambda_from_docker(function_name, image_uri, memory_size=2048, timeout=120):
    client = boto3.client('lambda')

    account_id = image_uri.split(".")[0]
    role_name = function_name
    create_lambda_execution_role(role_name)

    try:
        client.get_function(FunctionName=function_name)
        function_exists = True
    except client.exceptions.ResourceNotFoundException:
        function_exists = False

    if function_exists:
        response = client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri,
            Publish=True
        )
        print(response)
        while True:
            response = client.get_function_configuration(FunctionName=function_name)
            last_update_status = response.get('LastUpdateStatus', '')
            if last_update_status == 'Successful':
                break
            elif last_update_status == 'Failed':
                raise Exception(f"Function update failed: {response.get('LastUpdateStatusReason', '')}")
            time.sleep(1)  # Sleep for 5 seconds between polling attempts
    else:
        response = client.create_function(
            FunctionName=function_name,
            PackageType='Image',
            Code={
                'ImageUri': image_uri
            },
            Role=f'arn:aws:iam::{account_id}:role/{role_name}',
            MemorySize=memory_size,
            Timeout=timeout,
            TracingConfig={
                'Mode': 'Active'
            },
            Layers=[],
            Tags={},
            Environment={
                'Variables': {}
            },
            FileSystemConfigs=[]
        )


    return response['FunctionArn']


def create_bucket(bucket_name):
    s3_client = boto3.client('s3')
    region = os.environ["AWS_DEFAULT_REGION"]

    try:
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': region
            }
        )
        print(f"Successfully created bucket {bucket_name}.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"Bucket {bucket_name} already exists.")
        else:
            print(f"Error creating bucket {bucket_name}. Exception: {e}")
            raise e


def main():
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-1'

    func_name = "flock"
    image_uri = "270448519663.dkr.ecr.us-west-1.amazonaws.com/flock:latest"

    # bucket_name = "on-demand-dots-" + func_name.replace("_", "-")

    response = deploy_lambda_from_docker(func_name, image_uri, memory_size=4096, timeout=120)
    print(response)


    # for i in range(20):
    #     username = f"user{i}"
    #     bucket_name = f"flock-storage-{username}-1"
    #     grant_bucket_access(func_name, bucket_name)
        

    # for i in range(30):
    #     bucket_name = f"flock-aws-lambda-storage-user{i}"
    #     create_bucket(bucket_name)df

if __name__ == "__main__":
    main()
