

def str_index(string: bytes, substr: bytes):
    try:
        i = string.index(substr)
        return i
    except ValueError:
        return None