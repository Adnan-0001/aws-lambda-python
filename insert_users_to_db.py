import json
import os

import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("table_name"))


def encrypt_data(plaintext_data, key_alias):
    kms = boto3.client("kms")

    response = kms.describe_key(KeyId=f"alias/{key_alias}")
    key_id = response["KeyMetadata"]["KeyId"]

    response = kms.encrypt(KeyId=key_id, Plaintext=bytes(plaintext_data, "utf-8"))
    return response["CiphertextBlob"]


def extract_fields_and_insert_into_db(line):
    email = password = username = domain = ""
    separators = [":", ";", ","]
    for separator in separators:
        if separator in line:
            parts = line.split(separator)
            if len(parts) == 2:
                email = parts[0].strip()
                password = parts[1].strip()

                if "@" not in email:
                    username = email
                    email = domain = ""
                else:
                    username, domain = email.split("@")

                if password:
                    password = encrypt_data(
                        password, os.environ.get("kms_key", "master_key")
                    )

                try:
                    table.put_item(
                        Item={
                            "username": username,
                            "email": email,
                            "password": password,
                            "domain": domain,
                        }
                    )
                except ClientError as err:
                    logger.error(
                        "Couldn't add record %s. Here's why: %s: %s",
                        line,
                        err.response["Error"]["Code"],
                        err.response["Error"]["Message"],
                    )
                    return {
                        "statusCode": err.response["Error"]["Code"],
                        "body": json.dumps(
                            {
                                "msg": err.response["Error"]["Message"],
                            },
                        ),
                    }


def lambda_handler(event, context):
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    s3_file_name = event["Records"][0]["s3"]["object"]["key"]
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_file_name)
    data = response["Body"].read().decode("utf-8")
    records = data.split("\n")

    for record in records:
        extract_fields_and_insert_into_db(record.strip())
