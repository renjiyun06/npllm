def is_json_str(value):
    if value is None:
        return True
    return isinstance(value, str)

def is_json_number(value):
    if value is None:
        return True
    return isinstance(value, (int, float))

def is_json_bool(value):
    if value is None:
        return True
    return isinstance(value, bool)

def is_json_array(value):
    if value is None:
        return True
    return isinstance(value, list)

def is_json_object(value):
    if value is None:
        return True
    return isinstance(value, dict)

def is_json_null(value):
    return value is None