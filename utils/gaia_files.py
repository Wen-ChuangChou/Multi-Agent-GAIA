"""
GAIA dataset file resolver.

Bypasses the broken /files/{task_id} endpoint in the scoring Space by
downloading the GAIA dataset directly and building a task_id → local file
path mapping.

See: https://discuss.huggingface.co/t/get-files-task-id-returning-404-for-every-task-id-with-file-name/170575
"""

import os
from huggingface_hub import snapshot_download
from datasets import load_dataset


class GAIAFileResolver:
    """Resolves task_id to local file paths from the GAIA dataset."""

    def __init__(self):
        """
        Download the GAIA dataset and build the task_id → file_path mapping
        across all levels and splits.
        """
        print("Downloading GAIA dataset...")
        
        # We download directly to a local directory to avoid Windows symlink/cache issues
        local_gaia_dir = os.path.join(os.path.dirname(__file__), "..", "gaia_data")
        os.makedirs(local_gaia_dir, exist_ok=True)
        
        self.data_dir = snapshot_download(
            "gaia-benchmark/GAIA", 
            repo_type="dataset",
            local_dir=local_gaia_dir
        )
        print(f"GAIA dataset downloaded to: {self.data_dir}")

        self.id_to_path = {}
        total_tasks = 0

        # Load all configs and splits
        for config_name in ["2023_level1", "2023_level2", "2023_level3"]:
            for split in ["validation", "test"]:
                try:
                    ds = load_dataset("gaia-benchmark/GAIA", config_name, split=split)
                    total_tasks += len(ds)
                    for ex in ds:
                        if ex.get("file_path") and ex.get("file_name"):
                            full_path = os.path.join(self.data_dir, ex["file_path"])
                            if os.path.exists(full_path):
                                self.id_to_path[ex["task_id"]] = full_path
                except Exception as e:
                    print(f"Failed to load {config_name} {split}: {e}")

        print(f"Resolved {len(self.id_to_path)} file-bearing tasks "
              f"out of {total_tasks} total tasks.")

    def get_file_path(self, task_id: str) -> str | None:
        """
        Return the local file path for a given task_id, or None if no file.

        Args:
            task_id: The GAIA task identifier.

        Returns:
            Absolute path to the file on disk, or None.
        """
        return self.id_to_path.get(task_id)

    def has_file(self, task_id: str) -> bool:
        """Check whether a task has an associated file."""
        return task_id in self.id_to_path
