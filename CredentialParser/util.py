

from datetime import timedelta


def str_index(string: bytes, substr: bytes):
    try:
        i = string.index(substr)
        return i
    except ValueError:
        return None


def timestr(t: timedelta):
    m, s = divmod(t.total_seconds(), 60)
    h, m = divmod(m, 60)
    ts = []
    if h > 0:
        ts.append(f"{h:.0f}h")
    if m > 0:
        ts.append(f"{m:.0f}m")
    if s > 0:
        ts.append(f"{s:.0f}s")
    return " ".join(ts)
