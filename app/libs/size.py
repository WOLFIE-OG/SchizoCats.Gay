import math


def convertSize(bytes: int) -> tuple[str, float, str]:
    """_summary_

    Args:
        bytes (int): _description_

    Returns:
        _type_: _description_
    """
    if bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(bytes, 1024)))
    p = math.pow(1024, i)
    s = round(bytes / p, 2)
    return f"{s} {size_name[i]}", s, size_name[i]
