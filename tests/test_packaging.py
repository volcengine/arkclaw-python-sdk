# Copyright (c) 2026 Beijing Volcano Engine Technology Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path
import unittest

import arkclaw


ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_package_exports_runtime_options(self) -> None:
        self.assertTrue(hasattr(arkclaw, "RuntimeOptions"))
        self.assertTrue(hasattr(arkclaw, "TransportConfig"))

    def test_package_version_matches_distribution_metadata(self) -> None:
        self.assertEqual(arkclaw.__version__, importlib.metadata.version("arkclaw-python-sdk"))

    def test_required_open_source_files_exist(self) -> None:
        for name in (
            "LICENSE",
            "CHANGELOG.md",
            "SECURITY.md",
            "MANIFEST.in",
            "requirements.txt",
            ".github/pull_request_template.md",
        ):
            self.assertTrue((ROOT / name).exists(), name)

    def test_py_typed_marker_exists(self) -> None:
        self.assertTrue((ROOT / "arkclaw" / "py.typed").exists())

    def test_examples_are_importable_without_running_network_calls(self) -> None:
        for path in (ROOT / "examples").glob("*.py"):
            spec = importlib.util.spec_from_file_location(path.stem, path)
            self.assertIsNotNone(spec, path)
            self.assertIsNotNone(spec.loader, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertTrue(hasattr(module, "main"), path)


if __name__ == "__main__":
    unittest.main()
