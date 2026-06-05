import tempfile
import unittest
from pathlib import Path

from shed_agent.extract_listing import extract_listing
from shed_agent.storage import load_observations, save_observations


class StorageTests(unittest.TestCase):
    def test_save_observations_replaces_file_without_leaving_temp_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_path = Path(temp_dir) / "observations.json"
            observations = [extract_listing("Keter 6x5 vertical shed - $500")]

            save_observations(observations, data_path)

            self.assertEqual(len(load_observations(data_path)), 1)
            self.assertEqual(list(Path(temp_dir).glob(".observations.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
