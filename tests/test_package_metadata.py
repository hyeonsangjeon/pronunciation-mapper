import unittest
from importlib.metadata import version

from pronunciation_mapper import __version__


class TestPackageMetadata(unittest.TestCase):
    def test_runtime_version_matches_distribution_metadata(self):
        self.assertEqual(__version__, version("pronunciation-mapper"))


if __name__ == "__main__":
    unittest.main()
