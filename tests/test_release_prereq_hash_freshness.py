import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load_check_release_prereqs(project_root: Path):
    script_path = project_root / "scripts" / "check_release_prereqs.py"
    scripts_dir = str(project_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "check_release_prereqs_module",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load check_release_prereqs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReleasePrereqHashFreshness(unittest.TestCase):
    def test_hash_consistency_flags_stale_source_hash(self):
        repo_root = Path(__file__).resolve().parents[1]
        module = load_check_release_prereqs(repo_root)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "reports").mkdir(parents=True, exist_ok=True)
            (root / "scripts").mkdir(parents=True, exist_ok=True)

            # Ensure the fresh hash has deterministic non-empty content.
            (root / "scripts" / "dummy.py").write_text(
                "print('dummy')\n",
                encoding="utf-8",
            )

            stale_hash = "a" * 64
            (root / "reports" / "source_tree_hash_summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "pass": True,
                        "generated_at_utc": "2026-05-29T00:00:00Z",
                        "command": "hash",
                        "source_tree_hash": stale_hash,
                    }
                ),
                encoding="utf-8",
            )
            (root / "reports" / "source_tree_hash.txt").write_text(
                stale_hash + "\n",
                encoding="utf-8",
            )

            stamped = {
                "schema_version": 1,
                "pass": True,
                "generated_at_utc": "2026-05-29T00:00:00Z",
                "command": "dummy",
                "source_tree_hash": stale_hash,
            }
            for rel in module.HASH_STAMPED_JSONS:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(stamped), encoding="utf-8")

            module.PROJECT_ROOT = root
            result = module.require_hash_consistency()

            self.assertFalse(result["pass"])
            self.assertEqual(result["code"], "STALE_SOURCE_HASH")


if __name__ == "__main__":
    unittest.main()
