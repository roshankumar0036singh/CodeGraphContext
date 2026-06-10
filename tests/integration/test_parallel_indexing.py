import os
import tempfile
import unittest
import subprocess
from pathlib import Path

class TestParallelIndexing(unittest.TestCase):
    def test_indexing_serial_and_parallel(self):
        """Verify that both serial and parallel ProcessPoolExecutor indexing works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "test_repo"
            repo_path.mkdir()
            
            cgc_home_serial = Path(temp_dir) / "cgc_serial"
            cgc_home_parallel = Path(temp_dir) / "cgc_parallel"
            
            # Create some dummy python files
            for i in range(5):
                file_path = repo_path / f"test_{i}.py"
                file_path.write_text(f"def test_func_{i}():\n    pass\n")
            
            env = os.environ.copy()
            env["DEFAULT_DATABASE"] = "kuzudb"
            env["PYTHONPATH"] = "src"
            env["PYTHONIOENCODING"] = "utf-8"
            
            # Test Serial (1 worker)
            env["CGC_PARSE_WORKERS"] = "1"
            env["CGC_HOME"] = str(cgc_home_serial)
            result_serial = subprocess.run(
                ["python", "-m", "codegraphcontext.cli.main", "index", "--force", str(repo_path)],
                env=env, capture_output=True, text=True
            )
            self.assertEqual(result_serial.returncode, 0, msg=f"Serial failed: {result_serial.stderr}\n{result_serial.stdout}")
            self.assertIn("Successfully", result_serial.stdout)

            # Test Parallel (2 workers)
            env["CGC_PARSE_WORKERS"] = "2"
            env["CGC_HOME"] = str(cgc_home_parallel)
            result_parallel = subprocess.run(
                ["python", "-m", "codegraphcontext.cli.main", "index", "--force", str(repo_path)],
                env=env, capture_output=True, text=True
            )
            self.assertEqual(result_parallel.returncode, 0, msg=f"Parallel failed: {result_parallel.stderr}\n{result_parallel.stdout}")
            self.assertIn("Successfully", result_parallel.stdout)

if __name__ == '__main__':
    unittest.main()
