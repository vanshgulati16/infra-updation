import boto3
import json
import os
from dotenv import load_dotenv
load_dotenv()

# Open and load the taskdef.json file
with open('taskdef.json', 'r') as file:
    taskdef_data = json.load(file)

# Extract the required information
container_image = taskdef_data['containerDefinitions'][0]['image']  # Replace with your ECR image URI
conatiner_name = taskdef_data['containerDefinitions'][0]['name']  # Replace with your container name
task_defination_name = taskdef_data['family']   # Replace with your task definition name
task_definition_arn = taskdef_data['taskDefinitionArn']   # Replace with your task definition ARN
task_role_arn = taskdef_data['taskRoleArn']    # Replace with your task role ARN
task_execution_role_arn = taskdef_data['executionRoleArn']   # Replace with your task execution role ARN
aws_region = taskdef_data['containerDefinitions'][0]['logConfiguration']['options']['awslogs-region']   # Replace with your AWS region
aws_network_mode = taskdef_data['networkMode']    # Replace with your network mode
container_port = taskdef_data['containerDefinitions'][0]['portMappings'][0]['containerPort']    # Replace with your container port
protocol = taskdef_data['containerDefinitions'][0]['portMappings'][0]['protocol']    # Replace with your protocol
container_name = taskdef_data['containerDefinitions'][0]['name']
load_balancer_arn = taskdef_data['LoadBalancerArn']  # Replace with your load balancer ARN


# Configure AWS credentials and region
aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')

# Configure ECS and ELB clients
ecs = boto3.client('ecs')
elbv2 = boto3.client('elbv2')

# Define the service name and new microservice details
service_name = 'ecs-blue-green-new'   # Replace with your ECS service name which you want
new_microservice_name = 'ecs-blue-green-latest'    # Replace with the new that you want, this name would be used for target group and load balncer listener microservice name


# Step 1: Create a new task definition for the microservice
response = ecs.register_task_definition(
    family=new_microservice_name,
    taskRoleArn= task_role_arn,
    executionRoleArn= task_execution_role_arn,
    networkMode='awsvpc',
    cpu='256',
    memory='512',
    containerDefinitions=[
        {
            'name': f'{new_microservice_name}-container',
            'image': container_image,  # Replace with your ECR image URI
            'portMappings': [
                {
                    'containerPort': container_port,
                    'protocol': 'tcp'
                }
            ],
            'cpu': 256,  # Placeholder value, replace with your desired CPU units
            'memory': 512,  # Placeholder value, replace with your desired memory reservation in MiB
        }
    ]
)
task_definition_arn = response['taskDefinition']['taskDefinitionArn']
print(f"New Task Definition ARN: {task_definition_arn}")

# Step 2: Create a new target group for the microservice
response = elbv2.create_target_group(
    Name=f'{new_microservice_name}-TG',
    Protocol='HTTP',
    Port=container_port,
    VpcId='vpc-048b42853bc93e76b',    # Replace with your VPC ID
    TargetType='ip'
)
target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
print(f"New Target Group ARN: {target_group_arn}")

# Create the load balancer listener
response_listener = elbv2.create_listener(
    LoadBalancerArn=load_balancer_arn,   # Replace with your load balancer ARN
    Protocol='HTTP',
    Port=8081,
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': target_group_arn   # Set the blue target group as the default target
        }
    ]
)
listener_arn = response_listener['Listeners'][0]['ListenerArn']
print(f"New Listener ARN: {listener_arn}")



# Step 3: Create a new listener rule for the microservice
response = elbv2.create_rule(
    ListenerArn= listener_arn,  # Replace with your listener ARN
    Conditions=[
        {
            'Field': 'path-pattern',
            'Values': [
                '/new_microservice/*'
            ]
        }
    ],
    Priority=1,
    Actions=[
        {
            'Type': 'forward',
            'TargetGroupArn': target_group_arn   # Replace with your target group ARN
        },
    ]
)
listener_rule_arn = response['Rules'][0]['RuleArn']
print(f"New Listener Rule ARN: {listener_rule_arn}")

# Step 4: create  a new service for the microservice
response = ecs.create_service(
        cluster='ecs-blue-green-cluster',
        serviceName=f'{service_name}-service',
        taskDefinition= task_definition_arn,
        desiredCount=2,  # blue-green deployment with 2 instances
        deploymentConfiguration={
            'maximumPercent': 200,
            'minimumHealthyPercent': 100,
        },
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets':  [
                            "subnet-026a9e0304df29a30",
                            "subnet-0de918c1cb96a975c",
                            "subnet-0a25fb1aa7d28d3df",
                            "subnet-0d44f13cc61e9c627",
                            "subnet-03e11d915540fd1b6",
                            "subnet-0023617eb65ac057c"
                        ],
                'securityGroups': ['sg-043c0e56ff834dafc'],
                'assignPublicIp': 'ENABLED',
            },
        },
        loadBalancers=[
            {
                'targetGroupArn': target_group_arn,
                'containerName': container_name,   # Replace with your new used for target group and load balncer listener microservice name ,
                'containerPort': 8081,
            },
        ],
        launchType= 'FARGATE',
        healthCheckGracePeriodSeconds=60,
    )
print(f"Created Service ARN: {response['service']['serviceArn']}")


print(f"Code pipeline attributes all created successfully!")









