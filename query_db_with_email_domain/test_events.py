event_item_not_found_email = {
    "httpMethod": "GET",
    "queryStringParameters": {"email": "test@example.com"},
}

event_item_found_email = {
    "httpMethod": "GET",
    "queryStringParameters": {"email": "user1@example.com"},
}

event_item_not_found_domain = {
    "httpMethod": "GET",
    "queryStringParameters": {"domain": "wow.com"},
}

event_item_found_domain = {
    "httpMethod": "GET",
    "queryStringParameters": {"domain": "example.com"},
}

event_invalid_query = {
    "httpMethod": "GET",
    "queryStringParameters": {"username": "user1"},
}

event_invalid_method_post = {
    "httpMethod": "POST",
    "queryStringParameters": {"email": "user1@example.com"},
}

event_invalid_method_put = {
    "httpMethod": "PUT",
    "queryStringParameters": {"email": "user1@example.com"},
}

event_invalid_method_delete = {
    "httpMethod": "DELETE",
    "queryStringParameters": {"email": "user1@example.com"},
}
