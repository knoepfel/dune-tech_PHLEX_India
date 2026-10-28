"""Strict access to phlex configuration from Python plugins.

phlex's Python configuration object has no ``in`` test, and
``config.get(key, default)`` returns the default whenever a value cannot be
read, not only when the key is missing.  Values it cannot read include nested
arrays and numeric arrays whose first element is an integer but whose later
elements are not (e.g. ``[0, 1.5]``): the array's type is taken from its first
element.  Positions are therefore best given as strings such as ``'0 0 1.5'``.
"""


def get(config, key, default):
    """Return config[key], or default if the key is missing.

    Raises:
        ValueError: If the key is present but phlex cannot read its value.
    """
    try:
        return config[key]
    except KeyError as e:
        # phlex reports a missing key as "out of range"; anything else means the
        # key is present but its value could not be converted.
        if "out of range" in str(e):
            return default
        raise ValueError(f"configuration {key!r} could not be read: {e}") from None


def xyz(value) -> tuple[float, float, float]:
    """Parse a position given as [x, y, z] or as a string 'x y z' (or 'x, y, z')."""
    parts = value.replace(",", " ").split() if isinstance(value, str) else value
    if len(parts) != 3:
        raise ValueError(f"position {value!r} does not have 3 coordinates")
    x, y, z = (float(p) for p in parts)
    return x, y, z
