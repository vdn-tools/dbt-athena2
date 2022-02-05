import boto3
from botocore.exceptions import ProfileNotFound


def get_boto3_session(region_name, aws_profile_name="default"):
    try:
        boto3_session: boto3.session.Session = boto3.session.Session(
            region_name=region_name, profile_name=aws_profile_name
        )
    except ProfileNotFound:
        boto3_session: boto3.session.Session = boto3.session.Session(
            region_name=region_name
        )

    return boto3_session
