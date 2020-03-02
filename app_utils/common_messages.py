SUCCESS_RESPONSES = {
    "creation_success": "{}, created successfully!",
    "with_interval": "{}, scheduled successfully!",
    "update_success": "{}, updated successfully!",
    "deletion_success": "{}, deleted successfully!",
    "approval_success": "{}, approved successfully!",
    "edit_success": "{}, edited successfully!",
    "upload_success": "{}, uploaded successfully!",

}

ERROR_RESPONSES = {
    "inexistent_record_query_error": "{} record does not exist",
    "invalid_field_error": "Please input a valid {}",
    "empty_field_error": "{} cannot be empty",
    "required_field": "{} is required!",
    "not_allowed_field": "{} is not allowed!",
    "duplication_error": "{}, already exists!",
    "authorization_error": "You do not have permission to perform this action",
    "invalid_login_credentials": "Please, enter valid credentials",
    "invalid_mobile_number": "This mobile number {} is not valid. "
                             "It should not have less than 10 digits and "
                             "should only contain digits(0-9)",
    "invalid_date_format": "Incorrect data format for {}, "
                           "should be YYYY-MM-DD",
    "update_error": "You can't update a business,you're not assigned to!",
    "no_matching_ids": "There are no {}(s) matching IDs: {}.",
    "invalid_id": "The id {} should be a positive number starting from 1 or"
    " just a string of characters",
    "invalid_values": "{} contains invalid values",
    "wrong_param": "Please provide a valid parameter in the url",
    "csv_missing_field": "csv file is missing some column(s)",
    "csv_many_field": "csv file has more than the required column(s)",
    "country_city_mismatch": "Country {} doesnot have City {}",
    "csv_field_error": "Fields marked with * are mandatory",
    "payment_terms_cash_on_deliver": "Cash on delivery terms do not need "
    "credit days on row {}",
    "payment_terms_on_credit": "On credit payment terms requires "
    "at least 1 credit day or more on row {}"
}
