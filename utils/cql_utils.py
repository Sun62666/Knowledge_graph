import re


def escape_cql_value(value: str) -> str:
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "\\'")
    value = value.replace('"', '\\"')
    return value


def escape_relation_type(relation: str) -> str:
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', relation):
        return relation
    return f"`{relation}`"