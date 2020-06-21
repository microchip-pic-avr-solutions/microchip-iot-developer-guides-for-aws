import os
import boto3
import botocore
import json
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import binascii
from string import Template

iot = boto3.client('iot')
ZT_THING_TYPE_NAME = 'microchip-zero-touch-kit'
ZT_POLICY_NAME = "zt_policy"
ZT_POLICY_TEMPLATE = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iot:Connect"
            ],
            "Resource": [
                "arn:aws:iot:${region}:${account_id}:client/${iot:Connection.Thing.ThingName}"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iot:Publish",
                "iot:Receive"
            ],
            "Resource": [
                "arn:aws:iot:${region}:${account_id}:topic/${iot:Connection.Thing.ThingName}/*",
                "arn:aws:iot:${region}:${account_id}:topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iot:Subscribe"
            ],
            "Resource": [
                "arn:aws:iot:${region}:${account_id}:topicfilter/${iot:Connection.Thing.ThingName}/#",
                "arn:aws:iot:${region}:${account_id}:topicfilter/$aws/things/${iot:Connection.Thing.ThingName}/shadow/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iot:UpdateThingShadow",
                "iot:GetThingShadow"
            ],
            "Resource": [
                "arn:aws:iot:${region}:${account_id}:topic/$aws/things/${iot:Connection.Thing.ThingName}/shadow/*"
            ]
        }
    ]
}


def cert_get_skid(certificate_pem):

    cert = x509.load_pem_x509_certificate(data=bytearray(
        certificate_pem, "utf-8"), backend=default_backend())
    """
    The generated digest is the SHA1 hash of the subjectPublicKey ASN.1 bit string.
    This is the first recommendation in RFC 5280 section 4.2.1.2
    """
    ski = x509.SubjectKeyIdentifier.from_public_key(cert.public_key())

    return binascii.b2a_hex(ski.digest).decode('ascii')


def create_policy(account_id, region):
    """
    Creates the policy if it does not exist.
    """
    try:
        iot.get_policy(policyName=ZT_POLICY_NAME)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            policy_template = Template(
                json.dumps(ZT_POLICY_TEMPLATE, indent=4))
            policy_document = policy_template.safe_substitute(
                account_id=account_id, region=region)
            iot.create_policy(policyName=ZT_POLICY_NAME,
                                policyDocument=policy_document)
        else:
            raise e

def lambda_handler(event, context):
    region = os.environ['AWS_DEFAULT_REGION']
    account_id = event['awsAccountId']
    certificate_id = event['certificateId']

    response = iot.describe_certificate(certificateId=certificate_id)
    certificate_arn = response['certificateDescription']['certificateArn']

    subj_key_id = cert_get_skid(
        response['certificateDescription']['certificatePem'])

    print('Certificate Subject Key ID: {}'.format(subj_key_id))
    thing_name = subj_key_id

    response = iot.create_thing_type(thingTypeName=ZT_THING_TYPE_NAME)
    response = iot.create_thing(
        thingName=thing_name, thingTypeName=ZT_THING_TYPE_NAME)

    create_policy(account_id, region)

    iot.attach_principal_policy(
        policyName=ZT_POLICY_NAME,
        principal=certificate_arn)

    iot.attach_thing_principal(
        thingName=thing_name,
        principal=certificate_arn)

    response = iot.update_certificate(
        certificateId=certificate_id,
        newStatus='ACTIVE')
