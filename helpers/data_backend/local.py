from helpers.data_backend.base import BaseDataBackend
from pathlib import Path
from io import BytesIO
import os, logging

logger = logging.getLogger("LocalDataBackend")
logger.setLevel(os.environ.get("SIMPLETUNER_LOG_LEVEL", "WARNING"))


class LocalDataBackend(BaseDataBackend):
    def read(self, filepath, as_byteIO: bool = False):
        """Read and return the content of the file."""
        # Openfilepath as BytesIO:
        with open(filepath, "rb") as file:
            data = file.read()
        if not as_byteIO:
            return data
        return BytesIO(data)

    def write(self, filepath, data):
        """Write data to the specified file."""
        # Convert data to Bytes:
        if isinstance(data, str):
            data = data.encode("utf-8")
        with open(filepath, "wb") as file:
            file.write(data)

    def delete(self, filepath):
        """Delete the specified file."""
        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            raise FileNotFoundError(f"{filepath} not found.")

    def exists(self, filepath):
        """Check if the file exists."""
        return os.path.exists(filepath)

    def open_file(self, filepath, mode):
        """Open the file in the specified mode."""
        return open(filepath, mode)

    def list_files(self, str_pattern: str, instance_data_root: str):
        """
        List all files matching the pattern.
        Creates Path objects of each file found.
        """
        logger.debug(
            f"LocalDataBackend.list_files: str_pattern={str_pattern}, instance_data_root={instance_data_root}"
        )
        if instance_data_root is None:
            raise ValueError("instance_data_root must be specified.")

        def _rglob_follow_symlinks(path: Path, pattern: str):
            for p in path.glob(pattern):
                yield p
            for p in path.iterdir():
                if p.is_dir() and not p.is_symlink():
                    yield from _rglob_follow_symlinks(p, pattern)
                elif p.is_symlink():
                    real_path = Path(os.readlink(p))
                    if real_path.is_dir():
                        yield from _rglob_follow_symlinks(real_path, pattern)

        paths = list(_rglob_follow_symlinks(Path(instance_data_root), str_pattern))

        # Group files by their parent directory
        path_dict = {}
        for path in paths:
            parent = str(path.parent)
            if parent not in path_dict:
                path_dict[parent] = []
            path_dict[parent].append(str(path.absolute()))

        results = [(subdir, [], files) for subdir, files in path_dict.items()]
        return results

    def read_image(self, filepath):
        from PIL import Image
        # Remove embedded null byte:
        filepath = filepath.replace("\x00", "")
        try:
            image = Image.open(filepath)
            return image
        except Exception as e:
            logger.error(f"Encountered error opening image: {e}")
            raise e

    def create_directory(self, directory_path):
        os.makedirs(directory_path, exist_ok=True)

    def torch_load(self, filename):
        import torch

        return torch.load(self.read(filename, as_byteIO=True))

    def torch_save(self, data, filename):
        import torch

        torch.save(data, self.open_file(filename, "wb"))
