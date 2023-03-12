import boto3
from datetime import datetime, timedelta

def cleanup_resources():
    # Define the AWS services to clean up
    services = ['ec2', 'rds', 's3', 'lambda']

    # Define the time threshold for unused resources (in days)
    threshold = 30

    # Create a dictionary to store the unused resources for each service
    unused_resources = {}

    # Initialize the AWS clients for each service
    ec2_client = boto3.client('ec2')
    rds_client = boto3.client('rds')
    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')

    # Iterate over each service and find unused resources
    for service in services:
        unused_resources[service] = []

        if service == 'ec2':
            # Find unused EC2 instances
            response = ec2_client.describe_instances(
                Filters=[
                    {
                        'Name': 'instance-state-name',
                        'Values': ['stopped']
                    }
                ]
            )

            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    launch_time = instance['LaunchTime']
                    delta = datetime.now(launch_time.tzinfo) - launch_time
                    if delta.days >= threshold:
                        unused_resources[service].append(instance['InstanceId'])

        elif service == 'rds':
            # Find unused RDS instances
            response = rds_client.describe_db_instances()

            for instance in response['DBInstances']:
                if instance['DBInstanceStatus'] == 'stopped':
                    launch_time = instance['InstanceCreateTime']
                    delta = datetime.now(launch_time.tzinfo) - launch_time
                    if delta.days >= threshold:
                        unused_resources[service].append(instance['DBInstanceIdentifier'])

        elif service == 's3':
            # Find unused S3 buckets
            response = s3_client.list_buckets()

            for bucket in response['Buckets']:
                try:
                    response = s3_client.head_bucket(Bucket=bucket['Name'])
                except:
                    # Bucket does not exist or cannot be accessed
                    continue

                last_modified = response['LastModified']
                delta = datetime.now(last_modified.tzinfo) - last_modified
                if delta.days >= threshold:
                    unused_resources[service].append(bucket['Name'])

        elif service == 'lambda':
            # Find unused Lambda functions
            response = lambda_client.list_functions()

            for function in response['Functions']:
                response = lambda_client.list_tags(
                    Resource=function['FunctionArn']
                )

                if 'LastUsed' in response['Tags']:
                    last_used = datetime.fromisoformat(response['Tags']['LastUsed'])
                    delta = datetime.now(last_used.tzinfo) - last_used
                    if delta.days >= threshold:
                        unused_resources[service].append(function['FunctionArn'])

    # Delete unused resources
    for service, resources in unused_resources.items():
        for resource in resources:
            if service == 'ec2':
                ec2_client.terminate_instances(InstanceIds=[resource])
            elif service == 'rds':
                rds_client.delete_db_instance(
                    DBInstanceIdentifier=resource,
                    SkipFinalSnapshot=True
                )
            elif service == 's3':
                s3_client.delete_bucket(Bucket=resource)
            elif service == 'lambda':
                lambda_client.delete_function(FunctionName=resource)

    return unused_resources
