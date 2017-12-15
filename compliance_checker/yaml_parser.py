import yaml

from compliance_checker.base import BaseCheck, GenericFile, Dataset, MyMiscChecks


class YamlParser(object):
    """
    Class to hold methods relating to generating a checker class from a YAML config file
    """

    @classmethod
    def get_checker_class(cls, config):
        """
        Parse the given YAML file and return a checker class

        :param config: Config dictionary or filename of YAML file to parse config from
        """
        # Treat config as a filename if it is a string
        if isinstance(config, str):
            with open(config) as f:
                config = yaml.load(f)

            if not isinstance(config, dict):
                raise TypeError("Could not parse dictionary from YAML file")

        cls.validate_config(config)

        # Build the attributes and methods for the generated class
        class_properties = {
            "supported_ds": [GenericFile, Dataset]  # TODO: Get this from YAML?
        }

        for check_info in config["checks"]:
            method_name = "check_{}".format(check_info["check_id"])
            level = getattr(BaseCheck, check_info.get("check_level", "MEDIUM"))
            kwargs = {"name": method_name, "level": level}
            kwargs.update(check_info["params"])

            check_callable = getattr(MyMiscChecks, check_info["base_check"])

            # Create function that will become method of the new class. Specify
            # check_callable and kwargs as default arguments so that they are
            # evaluated when function is defined - otherwise the function stores
            # a reference to them which changes as the for loop
            # progresses, so only the last check is run
            def inner(self, ds, c=check_callable, kwargs=kwargs):
                return c(ds, kwargs.pop("name"), kwargs.pop("level"), **kwargs)

            inner.__name__ = str(method_name)
            class_properties[method_name] = inner

        return type(config["suite_name"], (BaseCheck,), class_properties)

    @classmethod
    def validate_config(cls, config):
        """
        Validate a config dict to check it has all the information required to generate a checker
        class

        :param config: The dictionary parsed from YAML file to check
        :raises ValueError: if any required values are missing or invalid
        :raises TypeError:  if any values are an incorrect type
        """
        required_global = {"checks": list, "suite_name": str}
        required_percheck = {"check_id": str, "params": dict, "base_check": str}
        optional_percheck = {"check_level": str}

        for f_name, f_type in required_global.items():
            cls.validate_field(f_name, f_type, config, True)

        for check_info in config["checks"]:
            for f_name, f_type in required_percheck.items():
                cls.validate_field(f_name, f_type, check_info, True)

            for f_name, f_type in optional_percheck.items():
                cls.validate_field(f_name, f_type, check_info, False)

            allowed_levels = ("HIGH", "MEDIUM", "LOW")
            if "check_level" in check_info and check_info["check_level"] not in allowed_levels:
                raise ValueError("Check level must be one of {}".format(", ".join(allowed_levels)))

        if len(config["checks"]) == 0:
            raise ValueError("List of checks cannot be empty")

    @classmethod
    def validate_field(cls, key, val_type, d, required):
        """
        Helper method to check a dictionary contains a given key and that the value is the
        correct type
        """
        if required:
            if key not in d:
                raise ValueError("Required key {} not present".format(key))
        if key in d and not isinstance(d[key], val_type):
            raise TypeError("Value for field {} is not of type {}".format(key, val_type.__name__))
