import boto3
from datetime import datetime, timedelta, timezone

# EC2 client
ec2 = boto3.client('ec2', region_name='us-east-1')

# EC2 resource
ec2_resource = boto3.resource('ec2', region_name='us-east-1')

# SNS client
sns_client = boto3.client('sns')

# Topic ARN created on AWS
my_topic = 'arn:aws:sns:us-east-1:042923755775:My-Topic'

# Get list of instances
response = ec2.describe_instances()

# Get instance ids as list
instance_ids = []

# Loop through instances to get instances with tag key "Name"
for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        for tag in instance['Tags']:
            if tag['Key'] == 'Name':
                instance_ids.append(instance['InstanceId'])

print(instance_ids)

# Create ami for each instance
for instance_id in instance_ids:
    # Get the 'Name' tag value
    instance = ec2.describe_instances(InstanceIds=[instance_id])
    instance_name = instance['Reservations'][0]['Instances'][0]['Tags'][0]['Value']

    try:
        # Create image
        image = ec2.create_image(
            InstanceId=instance_id,
            Name=instance_name + '-' + datetime.now().strftime('%Y-%m-%d'),
            NoReboot=True,
            Description='AMI from' + instance_id,
        )
        print(f"Successfully created AMI {image['ImageId']} for instance:{instance_id}")

        # Add tags
        ec2.create_tags(
            Resources=[image['ImageId']],
            Tags=[{
                'Key': 'Name',
                'Value': instance_name + '-' + datetime.now().strftime('%Y-%m-%d')
            }]
        )
        sns_client.publish(
            TopicArn=my_topic,
            Message=f'Created AMI for instance {instance_id}'
        )
    except Exception as e:
        print(f'Error creating AMI: {e}')
        sns_client.publish(
            TopicArn=my_topic,
            Message=f'Error creating AMI for instance {instance_id} with error: {e}'
        )

# Get all images in my account
images = ec2_resource.images.filter(Owners=['self'])

# Loop through the images and delete the old unused ones
for image in images:
    print(image.name + ' created on ' + image.creation_date)
    creation_date = datetime.strptime(image.creation_date, '%Y-%m-%dT%H:%M:%S.%fZ')
    age = datetime.now(timezone.utc).replace(tzinfo=None) - creation_date.replace(tzinfo=None)

    if age.days > 30:
        try:
            image.deregister()
            print(f'Deleted AMI {image.id}')
        except Exception as e:
            print(f'Exception while deleting AMI {image.id}: {e}')
            sns_client.publish(
                TopicArn=my_topic,
                Message=f'Exception while deleting AMI {image.id}: {e}'
            )
