

def str_index(string: str, substr: str):
    try:
        i = string.index(substr)
        return i
    except ValueError:
        return None