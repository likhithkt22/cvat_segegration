"""Small, dependency-free helper functions."""


import re


def safe_name(value):
    """
    Make a Windows-safe file/folder name.
    """
    invalid = '<>:"/\\|?*'
    return "".join(
        "_" if c in invalid else c
        for c in str(value)
    ).strip()


def parse_name_or_id(value):
    """
    Supports values such as:

        Project_1 #3
        testing #129

    Returns:
        name = Project_1
        id   = 3
    """
    value = str(value).strip()

    match = re.match(r"^(.*?)\s*#\s*(\d+)\s*$", value)

    if match:
        name = match.group(1).strip()
        object_id = int(match.group(2))
        return name, object_id

    return value, None
