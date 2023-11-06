import os
import random
import unittest

import moto
from boto3 import client, resource
from insert_users_to_db import (
    connect_and_read_data_from_s3,
    connect_to_table,
    extract_fields_and_insert_into_db,
)


@moto.mock_dynamodb
@moto.mock_s3
@moto.mock_kms
class TestInsertUsersToDB(unittest.TestCase):
    def _setup_mock_ddb(self):
        # Create the mock table
        self.test_ddb_table_name = "users"
        os.environ["table_name"] = self.test_ddb_table_name

        dynamodb = resource("dynamodb", region_name="us-east-1")
        key_schema = [{"AttributeName": "username", "KeyType": "HASH"}]
        attribute_definitions = [
            {"AttributeName": "username", "AttributeType": "S"},
        ]
        billing_mode = "PAY_PER_REQUEST"
        dynamodb.create_table(
            TableName=self.test_ddb_table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode=billing_mode,
        )

        dynamodb.Table(self.test_ddb_table_name).wait_until_exists()

    def _setup_mock_s3_bucket(self):
        self.test_s3_bucket_name = "data-bucket"
        s3_client = client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket=self.test_s3_bucket_name)

        # Put a file in the bucket
        self.test_file = "data.txt"
        self.test_file_content = "Hello, this is a test file."
        s3_client.put_object(
            Bucket=self.test_s3_bucket_name,
            Key=self.test_file,
            Body=self.test_file_content,
        )

    def _setup_mock_kms_client(self):
        self.kms_client = client("kms", region_name="us-east-1")
        response = self.kms_client.create_key()
        key_id = response["KeyMetadata"]["KeyId"]

        # Create an alias for the KMS key
        alias_name = "alias/testKey"
        self.kms_client.create_alias(AliasName=alias_name, TargetKeyId=key_id)

        os.environ["kms_key"] = "testKey"

    def setUp(self) -> None:
        self._setup_mock_ddb()
        self._setup_mock_s3_bucket()
        self._setup_mock_kms_client()

        self.table = connect_to_table()

    def test_read_from_s3(self):
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": self.test_s3_bucket_name},
                        "object": {"key": self.test_file},
                    }
                }
            ]
        }
        res = connect_and_read_data_from_s3(event)
        self.assertEqual(len(res), len(self.test_file_content.split("\n")))

    def test_extract_and_insert_into_db_pass(self):
        separators = [":", ";", ","]
        random_separator = random.choice(separators)

        line = f"gavi25@netvigator.co.uk{random_separator}gavinm"
        extract_fields_and_insert_into_db(self.table, line)
        response = self.table.get_item(Key={"username": "gavi25"})

        self.assertIn(
            "Item", response, "Item not found in the DynamoDB table."
        )

    def test_extract_and_insert_into_db_fail_no_separator(self):
        line = "gavi25@netvigator.co.ukgavinm"
        extract_fields_and_insert_into_db(self.table, line)
        response = self.table.get_item(Key={"username": "gavi25"})

        self.assertNotIn("Item", response, "Item should not be inserted")

    def test_extract_and_insert_into_db_fail_no_email(self):
        separators = [":", ";", ","]
        random_separator = random.choice(separators)

        line = f"gavi25netvigator.co.uk{random_separator}gavinm"
        extract_fields_and_insert_into_db(self.table, line)
        response = self.table.get_item(Key={"username": "gavi25"})

        self.assertNotIn("Item", response, "Item should not be inserted")


if __name__ == "__main__":
    unittest.main()
