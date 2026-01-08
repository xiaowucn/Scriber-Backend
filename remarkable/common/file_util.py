"""File utility functions for the Remarkable project."""

import os
import shutil


def copy_model_file(from_dir: str, to_dir: str, fname: str) -> str | None:
    """Copy model file from source to destination directory.

    Args:
        from_dir: Source directory path
        to_dir: Destination directory path
        fname: File or directory name to copy

    Returns:
        Path to the copied file/directory, or None if source doesn't exist
    """
    # clear existed file
    to_path = os.path.join(to_dir, fname)
    if os.path.exists(to_path):
        if os.path.isdir(to_path):
            shutil.rmtree(to_path)
        else:
            os.remove(to_path)

    # check from file
    from_path = os.path.join(from_dir, fname)
    if not os.path.exists(from_path):
        return None

    # copy file
    if os.path.isdir(from_path):
        shutil.copytree(from_path, to_path)
    else:
        _dir, _ = os.path.split(to_path)
        if not os.path.exists(_dir):
            os.makedirs(_dir)
        shutil.copy2(from_path, to_path)
    return to_path
