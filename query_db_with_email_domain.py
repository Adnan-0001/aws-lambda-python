import json
import logging
import os

import boto3
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.types import Binary
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def decrypt_data(encrypted_data):
    try:
        kms = boto3.client("kms")

        if isinstance(encrypted_data, Binary):
            encrypted_data = encrypted_data.value

        response = kms.decrypt(CiphertextBlob=encrypted_data)
        return response["Plaintext"].decode()
    except Exception as e:
        logger.error(
            "Error in decrypting data {}.".format(
                encrypted_data,
            )
        )
        raise e


def decrypt_password_from_records(items):
    for item in items:
        encrypted_password = item.get("password", None)
        if encrypted_password:
            item["password"] = decrypt_data(encrypted_password)


def connect_to_table():
    table = None
    try:
        TABLE_NAME = os.environ.get("table_name")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(TABLE_NAME)
        table.load()
    except ClientError as err:
        logger.error(
            "Couldn't load the table: %s. Here's why: %s: %s",
            TABLE_NAME,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise err
    return table


def lambda_handler(event, context):
    operation = event["httpMethod"]

    if operation != "GET":
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"msg": "Request type not supported"},
            ),
        }

    param_key = param_value = ""
    params = event["queryStringParameters"]

    if "email" in params:
        param_key = "email"
        param_value = event["queryStringParameters"]["email"]
    elif "domain" in params:
        param_key = "domain"

        param_value = event["queryStringParameters"]["domain"]
    else:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"msg": "Unknown parameter passed"},
            ),
        }

    table = connect_to_table()

    items = []
    try:
        filter_expression = Attr(param_key).eq(param_value)
        response = table.scan(FilterExpression=filter_expression)

        items = response["Items"]
        decrypt_password_from_records(items)

        while "LastEvaluatedKey" in response:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr(param_key).eq(
                    param_value
                ),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            data = response["Items"]
            decrypt_password_from_records(data)
            items.extend(data)
    except ClientError as err:
        logger.error(
            "Couldn't scan for records. Here's why: %s: %s",
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
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "msg": str(e),
                },
            ),
        }
    else:
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "data": items,
                    "count": len(items),
                },
            ),
        }
