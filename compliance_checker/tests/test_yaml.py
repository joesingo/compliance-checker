#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test the generation of a checker class from a YAML file
"""
import pytest
import inspect
from copy import deepcopy

from compliance_checker.tests import BaseTestCase
from compliance_checker.base import BaseCheck
from compliance_checker.yaml_parser import YamlParser


class TestYamlParsing(BaseTestCase):

    def test_missing_keys(self):
        """
        Check that a config with missing required fields is marked as invalid
        """
        invalid_configs = [
            {},
            {"suite_name": "hello"},  # Missing checks
            {"checks": []},           # Missing suite name
            {"suite_name": "hello", "checks": [{"check_id": "one"}]}
        ]
        valid_config = {"suite_name": "hello",
                        "checks": [{"check_id": "one", "params": {}}]}

        for c in invalid_configs:
            with pytest.raises(ValueError):
                YamlParser.validate_config(c)
        try:
            YamlParser.validate_config(valid_config)
        except ValueError:
            assert False, "Valid config was incorrectly marked as invalid"

    def test_invalid_types(self):
        """
        Check that configs are marked as invalid if elements in it are of the
        wrong type
        """
        # Start with a valid config
        valid_config = {"suite_name": "hello",
                        "checks": [{"check_id": "one", "params": {}}]}

        c1 = deepcopy(valid_config)
        c1["suite_name"] = ("this", "is", "not", "a", "string")

        c2 = deepcopy(valid_config)
        c2["checks"] = "oops"

        c3 = deepcopy(valid_config)
        c3["checks"][0]["check_id"] = {}

        c4 = deepcopy(valid_config)
        c4["checks"][0]["params"] = 0

        for c in (c1, c2, c3, c4):
            with pytest.raises(TypeError):
                YamlParser.validate_config(c)

    def test_no_checks(self):
        """
        Check that a config with no checks is invalid
        """
        with pytest.raises(ValueError):
            YamlParser.validate_config({"suite_name": "test", "checks": []})

    def test_class_gen(self):
        """
        Check that a checker class is generated correctly
        """
        # TODO: Specify base check so we can check it actually runs
        config = {
            "suite_name": "test_suite",
            "checks": [
                {"check_id": "one", "params": {}},
                {"check_id": "two", "params": {}}
            ]
        }
        new_class = YamlParser.get_checker_class(config)
        # Check class inherits from BaseCheck
        assert BaseCheck in new_class.__bases__

        # Check the expected methods are present
        method_names = [x[0] for x in inspect.getmembers(new_class, inspect.ismethod)]
        assert "check_one" in method_names
        assert "check_two" in method_names

        # Check name is correct
        assert new_class.__name__ == "test_suite"

