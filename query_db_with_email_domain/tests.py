import json
import os
import unittest
from unittest.mock import patch

import moto
from boto3 import client, resource
from query_db_with_email_domain import connect_to_table, lambda_handler
from test_events import (
    event_invalid_method_delete,
    event_invalid_method_post,
    event_invalid_method_put,
    event_invalid_query,
    event_item_found_domain,
    event_item_found_email,
    event_item_not_found_domain,
    event_item_not_found_email,
)


@moto.mock_dynamodb
@moto.mock_kms
class TestQueryDbAPI(unittest.TestCase):
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
        self._setup_mock_kms_client()

        self.table = connect_to_table()

        # Add dummy records to the table
        items = [
            {
                "username": "user1",
                "email": "user1@example.com",
                "password": "password1",
                "domain": "example.com",
            },
            {
                "username": "user2",
                "email": "user2@example.com",
                "password": "password2",
                "domain": "example.com",
            },
        ]

        for item in items:
            self.table.put_item(Item=item)

    @patch("query_db_with_email_domain.decrypt_data")
    def test_email_query_pass(self, decrypt_data_mock):
        decrypt_data_mock.return_value = "decrypted"
        response = lambda_handler(event_item_found_email, None)
        body = json.loads(response["body"])

        self.assertEqual(200, response.get("statusCode"))
        self.assertEqual(1, body["count"])

    @patch("query_db_with_email_domain.decrypt_data")
    def test_domain_query_pass(self, decrypt_data_mock):
        decrypt_data_mock.return_value = "decrypted"
        response = lambda_handler(event_item_found_domain, None)
        body = json.loads(response["body"])

        self.assertEqual(200, response.get("statusCode"))
        self.assertEqual(2, body["count"])

    @patch("query_db_with_email_domain.decrypt_data")
    def test_domain_query_fail(self, decrypt_data_mock):
        decrypt_data_mock.return_value = "decrypted"
        response = lambda_handler(event_item_not_found_domain, None)
        body = json.loads(response["body"])

        self.assertEqual(200, response.get("statusCode"))
        self.assertEqual(0, body["count"])

    @patch("query_db_with_email_domain.decrypt_data")
    def test_email_query_fail(self, decrypt_data_mock):
        decrypt_data_mock.return_value = "decrypted"
        response = lambda_handler(event_item_not_found_email, None)
        body = json.loads(response["body"])

        self.assertEqual(200, response.get("statusCode"))
        self.assertEqual(0, body["count"])

    def test_invalid_query_fail(self):
        response = lambda_handler(event_invalid_query, None)

        self.assertEqual(400, response.get("statusCode"))

    def test_invalid_method_post_fail(self):
        response = lambda_handler(event_invalid_method_post, None)

        self.assertEqual(400, response.get("statusCode"))

    def test_invalid_method_put_fail(self):
        response = lambda_handler(event_invalid_method_put, None)

        self.assertEqual(400, response.get("statusCode"))

    def test_invalid_method_delete_fail(self):
        response = lambda_handler(event_invalid_method_delete, None)

        self.assertEqual(400, response.get("statusCode"))


if __name__ == "__main__":
    unittest.main()
