# logging
import logging
# set up logging before importing sub modules
from validateJSON.logs import setup_logging
# configure logging
logger = setup_logging(logging.getLogger(__name__))


class JSONValidator:
    """
        validate JSON data using data schema

        the data schema consists of:
        - expected_keys: list of dicts describing the types & names
                         of each JSON parameter that MUST be in the
                         JSON object
        - conditional_keys: list of dicts describing the type, name
                            and dependence info of a set of each JSON
                            parameter that MUST be in the JSON
                            object
        - optional_keys: list of dicts describing the types & names
                         of each JSON parameter that may or may not
                         be in the JSON object (only checked for types)
    """
    def validate_expected(self, json_object, expected_keys):
        """
            recursively checks to see if a list of parameters are in a
            given JSON object and have the right type. list of
            parameters are dict objects of the form :-

            # nested
            expected_key_one =
                {
                    "param_name": "store_info",
                    "param_type": dict,
                    "expected_keys": [
                        {"param_name": "host", "param_type": str},
                        {"param_name": "dbname", "param_type": str},
                        {"param_name": "user", "param_type": str},
                        {"param_name": "password", "param_type": str},
                        {"param_name": "port", "param_type": int}
                    ]
                }
            # simple
            expected_key_two =
                {
                    "param_name": "source_type",
                    "param_type": str,
                    "possible_values": ["local", "azure_storage"]
                }
            # conditional
            expected_key_three =
                {
                    "param_name": "source_info",
                    "param_type": dict,
                    "conditional_keys": {
                        "depends_on": "source_type",
                        "dependence_info": {
                            "local": {
                                "expected_keys": [
                                    {"param_name": "file_path", "param_type": str}
                                ],
                                "optional_keys": [
                                    {"param_name": "dir_path", "param_type": str},
                                ]
                            },
                            "azure_storage": {
                                "expected_keys": [
                                    {"param_name": "connection_string", "param_type": str},
                                    {"param_name": "container_name", "param_type": str},
                                ],
                                "optional_keys": [
                                    {"param_name": "file_name", "param_type": str}
                                ]
                            }
                        }
                    }
                }

            params:
                - json_object: JSON object being validated
                - expected_keys: list of dicts describing JSON object
            returns
                - True or False
        """
        # validate all expected parameters are in JSON object
        contains_params = [
            # expected key in json for each expected key
            parameter in json_object for parameter in
            [expected_key["param_name"] for expected_key in expected_keys]
        ]
        # if there are any missing expected parameters
        if not all(contains_params):
            # log
            logger.error("missing expected parameter")
            # return False (invalid JSON object)
            return False
        # if there are no missing expected parameters
        else:
            # validate expected parameters' types
            correct_types = [
                # compare types
                isinstance(
                    # get value from json object
                    json_object[expected_key["param_name"]],
                    # get expected type from schema
                    expected_key["param_type"]
                )
                # for each expected param
                for expected_key in expected_keys
            ]
            # if there are any expected parameters with an incorrect type
            if not all(correct_types):
                # log
                logger.error("incorrect expected parameter type")
                # return False (invalid JSON object)
                return False
            # if there are no parameters with incorrect types
            else:
                # for each expected parameter
                for expected_key in expected_keys:
                    # possible values validation here
                    # (similar to ENUM in SQL)
                    if "possible_values" in expected_key:
                        # if val in JSON is one of possible vals
                        if json_object[expected_key["param_name"]] not in expected_key["possible_values"]:
                            # log
                            logger.error("incorrect expected parameter value")
                            # return False (invalid JSON object)
                            return False
                    # if expected key type is dict (nested JSON)
                    if expected_key["param_type"] == dict:
                        # if expected keys specified in schema for nested dict
                        if "expected_keys" in expected_key:
                            # recursively run above logic on any nested
                            # JSON object (i.e. any params of type dict)
                            if not self.validate_expected(
                                # get value of dict from JSON object
                                json_object[expected_key["param_name"]],
                                # get expected keys from schema
                                expected_key["expected_keys"]
                            ):
                                return False
                        if "conditional_keys" in expected_key:
                            # get the value the conditional keys depend on
                            depends_on_val = json_object[expected_key["conditional_keys"]["depends_on"]]
                            # get depdendence info (i.e. based on the above value
                            # get what the expected / optional keys are)
                            nested_optional_keys = expected_key["conditional_keys"]["dependence_info"][depends_on_val]["optional_keys"]
                            nested_expected_keys = expected_key["conditional_keys"]["dependence_info"][depends_on_val]["expected_keys"]
                            # recursively run optional & expected validation
                            return self.validate(
                                json_object[expected_key["param_name"]],
                                nested_expected_keys,
                                nested_optional_keys
                            )
                # return True (valid JSON object)
                return True

    def validate_optional(self, json_object, optional_keys):
        """
            recursively check the types of a given set of
            parameters if they exist in a given JSON object.
            list of parameters are dict objects of the form :-

            optional_key =
                {
                    "param_name": "source_type",
                    "param_type": str,
                }

            params:
                - json_object: JSON object being validated
                - expected_keys: list of dicts describing JSON object
            returns
                - True or False
        """
        # for all optional keys
        for optional_key in optional_keys:
            # if they are in the json object
            if optional_key["param_name"] in json_object:
                # validate optional types
                correct_type = isinstance(
                    # get value from JSON object
                    json_object[optional_key["param_name"]],
                    # get type from schema
                    optional_key["param_type"])
                # if not correct type
                if not correct_type:
                    # log
                    logger.error("invalid optional parameter type")
                    # return False (invalid JSON object)
                    return False
                # if optional parameter is a nested JSON
                if optional_key["param_type"] == dict:
                    # if it has optional parameters specified
                    if "optional_keys" in optional_key:
                        # run validation recursively
                        return self.validate_optional(
                            # pass nested JSON object
                            json_object[optional_key["param_name"]],
                            # pass nested JSON object schema
                            optional_key["optional_keys"]
                        )
        return True

    def validate(self, json_object, expected_keys, optional_keys=None):
        """
            check if a given JSON object
            - contains a given set of keys with given types
            - contains conditional parameters whose value & type is
            determined by expected keys
            - contains optional parameters with given types
        """
        # get name of valid keys from schema (expected + optional)
        if optional_keys is not None:
            # get names of valid parameters
            valid_keys = [expected_key["param_name"] for expected_key in expected_keys] + [optional_key["param_name"] for optional_key in optional_keys]
        # no optional parameters specified
        else:
            # get names of valid parameters
            valid_keys = [expected_key["param_name"] for expected_key in expected_keys]
        # check if any parameter present in json object that is not in valid_keys
        contains_valid = [
            # for each param in json object
            parameter in valid_keys for parameter in json_object
        ]
        # if any invalid parameter detected
        if not all(contains_valid):
            # log
            logger.error("invalid parameter detected")
            # return False (invalid JSON object)
            return False
        # run expected validation
        if self.validate_expected(json_object, expected_keys):
            # if optional parameters are specified
            if optional_keys is not None:
                # run optional validation
                if self.validate_optional(json_object, optional_keys):
                    # return success
                    return True
                else:
                    # return failure
                    return False
            # no optional keys specified return
            else:
                return True
        # validation failure
        else:
            return False
