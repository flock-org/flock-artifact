import boto3
import json

TASK_NAME="flock-task"
ECS_ROLE_NAME="flock-ecs"
TASK_ROLE_NAME="flock-s3-access"
CLUSTER_NAME = 'flock_cluster'
CONTAINER_IMAGE = "270448519663.dkr.ecr.us-west-1.amazonaws.com/flock:latest"

# CONTAINER_IMAGE="sijuntan/flock"
TASK_FAMILY = 'flock-task-family'
LOG_GROUP_NAME = "ecs/flock-ecs-logs"
REGION = "us-west-1"

def create_ecs_execution_role(role_name):
    # Initialize IAM client
    iam = boto3.client('iam')

    # Specify the assume role policy document
    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # Create the role
        create_role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description='ECS Task Execution Role',
        )

        # Attach the AmazonECSTaskExecutionRolePolicy policy
        policy_arn = 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )

        role_arn = create_role_response['Role']['Arn']
        print(f"Role created with ARN: {role_arn}")
        return role_arn

    except Exception as e:
        print(f"Error creating role: {e}")
        return None
    

def get_execution_role_arn(role_name):
    # Initialize IAM client
    iam = boto3.client('iam')
    
    try:
        # Get the role
        response = iam.get_role(RoleName=role_name)
        role_arn = response['Role']['Arn']
        print(f"Role ARN for {role_name}: {role_arn}")
        return role_arn
    except Exception as e:
        print(f"Error getting role: {e}")
        return None


def register_task_definition(task_definition_name, execution_role_arn, task_role_arn, container_image, port=5000):
    # Initialize ECS client
    ecs = boto3.client('ecs')
    
    # Define the container definitions
    container_definitions = [
        {
            'name': task_definition_name,
            'image': container_image,
            'cpu': 2048,
            'memory': 4096,
            'essential': True,
            # 'portMappings': [
            #     {
            #         'containerPort': port,
            #         'hostPort': port
            #     }
            # ],
            'portMappings': [{'containerPort': port, 'hostPort': port} for port in range(5000, 6100)],
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': LOG_GROUP_NAME,
                    'awslogs-region': REGION,
                    'awslogs-stream-prefix': 'ecs'
                }
            }
        }
    ]
    
    try:
        # Register the task definition
        response = ecs.register_task_definition(
            family=task_definition_name,
            executionRoleArn=execution_role_arn,
            taskRoleArn=task_role_arn,
            containerDefinitions=container_definitions,
            requiresCompatibilities=['FARGATE'],
            cpu='2048',
            memory='4096',
            networkMode='awsvpc'
        )
        
        # Print the task definition ARN
        task_definition_arn = response['taskDefinition']['taskDefinitionArn']
        print(f"Task definition registered with ARN: {task_definition_arn}")
        return task_definition_arn
        
    except Exception as e:
        print(f"Error registering task definition: {e}")
        return None


def describe_task_definition(task_definition_name):
    # Initialize ECS client
    ecs = boto3.client('ecs')
    
    try:
        # Describe the task definition
        response = ecs.describe_task_definition(
            taskDefinition=task_definition_name
        )
        # Print the task definition details
        print(f"Details for task definition {task_definition_name}:")
        print(response['taskDefinition'])
        
    except Exception as e:
        print(f"Error describing task definition {task_definition_name}: {e}")


def get_subnets(vpc_id=None):
    # Initialize EC2 client
    ec2 = boto3.client('ec2')
    
    # Define filters
    filters = []
    if vpc_id:
        filters.append({
            'Name': 'vpc-id',
            'Values': [vpc_id]
        })
    
    # Describe subnets
    try:
        response = ec2.describe_subnets(Filters=filters)
        subnet_ids = [subnet['SubnetId'] for subnet in response['Subnets']]
        return subnet_ids
    except Exception as e:
        print(f"Error getting subnets: {e}")
        return None
    

def get_default_vpc_id():
    # Initialize EC2 client
    ec2 = boto3.client('ec2')
    
    try:
        # Describe VPCs to find the default VPC
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        default_vpc_id = vpcs['Vpcs'][0]['VpcId'] if vpcs['Vpcs'] else None
        
        if not default_vpc_id:
            print("No default VPC found.")
            return None
        return default_vpc_id
        
    except Exception as e:
        print(f"Error getting default VPC id: {e}")
        return None

def get_default_vpc_subnets():
    # Initialize EC2 client
    ec2 = boto3.client('ec2')
    
    try:
        # Describe VPCs to find the default VPC
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        default_vpc_id = vpcs['Vpcs'][0]['VpcId'] if vpcs['Vpcs'] else None
        
        if not default_vpc_id:
            print("No default VPC found.")
            return None
        
        # Describe subnets in the default VPC
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [default_vpc_id]}])
        subnet_ids = [subnet['SubnetId'] for subnet in subnets['Subnets']]
        
        return subnet_ids
        
    except Exception as e:
        print(f"Error getting default VPC subnets: {e}")
        return None
    

def get_default_vpc_security_groups():
    # Initialize EC2 client
    ec2 = boto3.client('ec2')
    
    try:
        # Describe VPCs to find the default VPC
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        default_vpc_id = vpcs['Vpcs'][0]['VpcId'] if vpcs['Vpcs'] else None
        
        if not default_vpc_id:
            print("No default VPC found.")
            return None
        
        # Describe security groups in the default VPC
        security_groups = ec2.describe_security_groups(Filters=[{'Name': 'vpc-id', 'Values': [default_vpc_id]}])
        security_group_ids = [sg['GroupId'] for sg in security_groups['SecurityGroups']]
        
        return security_group_ids
        
    except Exception as e:
        print(f"Error getting security groups in default VPC: {e}")
        return None

    
def run_fargate_task(cluster_name, task_definition_name, subnets, security_groups):
    # Initialize ECS client
    ecs = boto3.client('ecs')
    
    try:
        # Run the Fargate task
        response = ecs.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition_name,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': subnets,
                    'securityGroups': security_groups,
                    'assignPublicIp': 'ENABLED'
                }
            },
            count=1
        )
        
        # Print the task ARN
        task_arn = response['tasks'][0]['taskArn']
        print(f"Fargate task launched with ARN: {task_arn}")
        return task_arn
        
    except Exception as e:
        print(f"Error launching Fargate task: {e}")
        return None
    

def stop_fargate_task(cluster_name, task_arn):
    # Initialize ECS client
    ecs = boto3.client('ecs')
    
    try:
        # Stop the Fargate task
        response = ecs.stop_task(
            cluster=cluster_name,
            task=task_arn,
            reason='Stopping task'
        )
        
        # Print the stopped task ARN
        stopped_task_arn = response['task']['taskArn']
        print(f"Fargate task stopped with ARN: {stopped_task_arn}")
        return stopped_task_arn
        
    except Exception as e:
        print(f"Error stopping Fargate task: {e}")
        return None
    

def create_and_attach_scp(profile_name, ou_id, scp_name, scp_description, scp_policy):
    """
    Creates an SCP and attaches it to the specified Organizational Unit.
    
    :param profile_name: AWS CLI profile name
    :param ou_id: Organizational Unit ID to attach the SCP to
    :param scp_name: Name of the SCP
    :param scp_description: Description of the SCP
    :param scp_policy: SCP policy in JSON format
    :return: A dictionary with the status of SCP creation and attachment
    """
    session = boto3.Session(profile_name=profile_name)
    organizations = session.client('organizations')
    
    response_dict = {
        'SCP_Creation': 'Failed',
        'SCP_Attachment': 'Failed'
    }
    
    try:
        response = organizations.create_policy(
            Content=json.dumps(scp_policy),
            Description=scp_description,
            Name=scp_name,
            Type='SERVICE_CONTROL_POLICY'
        )
        scp_id = response['Policy']['PolicySummary']['Id']
        response_dict['SCP_Creation'] = f"Success: {scp_id}"
    except Exception as e:
        response_dict['SCP_Creation'] = str(e)
        return response_dict
    
    try:
        response = organizations.attach_policy(
            PolicyId=scp_id,
            TargetId=ou_id
        )
        response_dict['SCP_Attachment'] = f"Success: {ou_id}"
    except Exception as e:
        response_dict['SCP_Attachment'] = str(e)
    
    return response_dict


def invite_account_to_organization(profile_name, account_id_to_invite, note):
    """
    Invites the specified AWS account to the AWS Organization.
    
    :param profile_name: AWS CLI profile name
    :param account_id_to_invite: AWS Account ID to invite
    :param note: Note to include in the invitation
    :return: Response from AWS Organizations API
    """
    session = boto3.Session(profile_name=profile_name)
    organizations = session.client('organizations')
    
    try:
        response = organizations.invite_account_to_organization(
            Target={
                'Id': account_id_to_invite,
                'Type': 'ACCOUNT'
            },
            Notes=note
        )
        return response
    except Exception as e:
        return str(e)


def accept_organization_invitation(profile_name, handshake_id):
    """
    Accepts an invitation to join an AWS Organization.
    
    :param profile_name: AWS CLI profile name
    :param handshake_id: Handshake ID received in the invitation
    :return: Response from AWS Organizations API
    """
    session = boto3.Session(profile_name=profile_name)
    organizations = session.client('organizations')
    
    try:
        response = organizations.accept_handshake(
            HandshakeId=handshake_id
        )
        return response
    except Exception as e:
        return str(e)
    

def create_log_group(log_group_name):
    logs = boto3.client('logs')
    logs.create_log_group(logGroupName=log_group_name)


def create_open_security_group(vpc_id, group_name='AllPortsOpen', description='Security group with all ports open'):
    ec2 = boto3.client('ec2')
    
    # Create Security Group
    try:
        response = ec2.create_security_group(GroupName=group_name,
                                             Description=description,
                                             VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))
        
        # Allow all incoming traffic
        try:
            data = ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': '-1',
                     'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ]
            )
            print('Ingress Successfully Set %s' % data)
        except Exception as e:
            print("Error occurred while setting ingress:", str(e))
            return None
        
        return security_group_id
        
    except Exception as e:
        print("Error occurred while creating security group:", str(e))
        return None


def get_security_group_by_name(group_name):
    ec2 = boto3.client('ec2')
    
    try:
        # Describe security group with the given group name
        response = ec2.describe_security_groups(
            Filters=[
                {'Name': 'group-name', 'Values': [group_name]}
            ]
        )
        
        # Check if any security groups are found
        if response and response.get('SecurityGroups'):
            security_group = response['SecurityGroups'][0]  # Get the first security group in the response
            return security_group
        else:
            print(f"No security group found with name: {group_name}")
            return None
    except Exception as e:
        print(f"Error occurred while getting security group by name: {str(e)}")
        return None
    
def create_s3_access_role(role_name):
    # Initialize IAM client
    iam = boto3.client('iam')

    # Define the trust relationship policy document
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        # Create the IAM role
        create_role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )

        # Attach the S3 full access policy to the role
        policy_arn = 'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )

        # Get and return the ARN of the newly created role
        role_arn = create_role_response['Role']['Arn']
        print(f"Role created with ARN: {role_arn}")
        return role_arn

    except Exception as e:
        print(f"Error creating S3 access role: {e}")
        return None
    

def get_iam_role_arn(role_name):
    try:
        # Initialize IAM client
        iam = boto3.client('iam')
        
        # Get the role
        response = iam.get_role(RoleName=role_name)
        
        # Extract and return the role ARN
        role_arn = response['Role']['Arn']
        return role_arn
    
    except Exception as e:
        print(f"Error getting IAM role ARN: {e}")
        return None
    
def get_fargate_task_ip(task_arn):
    """
    Retrieve the IP address of a Fargate task using its ARN.

    Parameters:
    - task_arn (str): The Amazon Resource Name (ARN) of the Fargate task.

    Returns:
    str: The IP address of the Fargate task.
    """
    # Create an ECS client
    ecs_client = boto3.client('ecs')
    
    # Describe the task
    response = ecs_client.describe_tasks(
        tasks=[task_arn]
    )
    
    # Check if tasks are returned in the response
    if response.get('tasks'):
        # Get the network interfaces
        network_interfaces = response['tasks'][0].get('attachments', [{}])[0].get('details', [])
        
        # Find the IP address from the network interfaces
        for interface in network_interfaces:
            if interface.get('name') == 'networkInterfaceId':
                eni_id = interface.get('value')
                
                # Create an EC2 client
                ec2_client = boto3.client('ec2')
                
                # Describe the network interface to get the IP address
                eni_response = ec2_client.describe_network_interfaces(
                    NetworkInterfaceIds=[eni_id]
                )
                
                # Check if an interface is returned in the response
                if eni_response.get('NetworkInterfaces'):
                    # Return the private IP address of the task
                    return eni_response['NetworkInterfaces'][0].get('PrivateIpAddress')
                
    # Return None if IP address is not found
    return None


def create_ecs_cluster(cluster_name):
    """
    Create an Amazon ECS cluster.

    Parameters:
        cluster_name (str): The name of the cluster to create.

    Returns:
        dict: The response from the create_cluster API call.
    """
    # Create an ECS client
    ecs_client = boto3.client('ecs')  # specify your desired region
    
    try:
        # Create cluster
        response = ecs_client.create_cluster(
            clusterName=cluster_name
        )
        print(f"Cluster {cluster_name} created successfully.")
        return response
    except Exception as e:
        print(f"Error creating cluster: {str(e)}")
        return None



if __name__ == "__main__":
    # create_ecs_cluster(CLUSTER_NAME)

    # create_log_group(LOG_GROUP_NAME)
    # vpc_id = get_default_vpc_id()
    # create_open_security_group(vpc_id)

    exec_role_arn = get_execution_role_arn(ECS_ROLE_NAME)
    if exec_role_arn is None:
        exec_role_arn = create_ecs_execution_role(ECS_ROLE_NAME)
    task_role_arn = get_iam_role_arn(TASK_ROLE_NAME)
    if task_role_arn is None:
        task_role_arn = create_s3_access_role(TASK_ROLE_NAME)
    # task_definition_arn = describe_task_definition(TASK_NAME)
    # if task_definition_arn is None:
    task_definition_arn = register_task_definition(TASK_NAME, exec_role_arn, task_role_arn, CONTAINER_IMAGE)

    subnets = get_default_vpc_subnets()
    # sg = get_default_vpc_security_groups()
    # print(sg)
    sg = [get_security_group_by_name("AllPortsOpen")["GroupId"]]
    fg_task_arn = run_fargate_task(CLUSTER_NAME, TASK_NAME, subnets, sg)
    print(fg_task_arn)


    # print(get_fargate_task_ip(TASK_NAME))