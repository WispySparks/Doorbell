"""Contains useful functions that are called frequently."""

from pathlib import Path


def relative_path_from_root(path: str) -> Path:
    """Creates an absolute path to a file or directory starting relative to the root of the repository.
    Used to ensure that paths work when running the program from any directory.
    For example passing in `test.txt` will return the path to that file relative to the root of this project so
    it might return `~/Projects/Doorbell/test.txt`."""
    return (Path(__file__).parent.parent / path).resolve()
