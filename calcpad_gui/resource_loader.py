"""UTF-8 package resources; independent of process working directory."""
from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=None)
def read_resource(name: str) -> str:
    """Read bundled literal bytes without newline conversion."""
    return files("calcpad_gui.resources").joinpath(name).read_bytes().decode("utf-8")
