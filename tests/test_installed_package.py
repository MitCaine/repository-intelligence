"""Offline wheel smoke test from an unrelated mixed-language directory."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def run(*args: object, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                            text=True, capture_output=True, check=True, timeout=120)
    return result.stdout


class InstalledPackageTests(unittest.TestCase):
    def test_offline_wheel_works_outside_source_tree(self):
        required = os.environ.get("RI_REQUIRE_STANDALONE") == "1"
        names = ("RI_SETUPTOOLS_WHEEL", "RI_WHEEL_WHEEL")
        wheels = [Path(os.environ[name]).resolve() for name in names if os.environ.get(name)]
        grammar_wheels = Path(os.environ.get("RI_TREE_SITTER_WHEELHOUSE", ""))
        if (len(wheels) != 2 or not all(path.is_file() for path in wheels)
                or not grammar_wheels.is_dir()):
            message = "offline build and Tree-sitter wheels are required"
            if required:
                self.fail(message)
            self.skipTest(message)

        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        environment.update(PIP_NO_INDEX="1", PIP_NO_CACHE_DIR="1",
                           PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONDONTWRITEBYTECODE="1")
        with tempfile.TemporaryDirectory(prefix="ri-installed-") as raw:
            temp = Path(raw)
            build, install, output = (temp / name for name in ("build", "install", "wheels"))
            consumer = temp / "neutral-consumer"
            run(sys.executable, "-m", "venv", build, env=environment)
            build_python = build / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run(build_python, "-m", "pip", "install", "--no-index", "--no-deps",
                *wheels, env=environment)
            output.mkdir()
            run(build_python, "-m", "pip", "wheel", "--no-index", "--no-build-isolation",
                "--no-deps", "--wheel-dir", output, ROOT, cwd=temp, env=environment)
            built = list(output.glob("repository_intelligence-*.whl"))
            self.assertEqual(len(built), 1)
            with zipfile.ZipFile(built[0]) as archive:
                modules = {name for name in archive.namelist()
                           if name.startswith("repository_intelligence/") and name.endswith(".py")}
            self.assertEqual(modules, {"repository_intelligence/__init__.py",
                                       "repository_intelligence/rust_index.py",
                                       "repository_intelligence/rust_tree_index.py",
                                       "repository_intelligence/python_index.py",
                                       "repository_intelligence/python_tree_index.py",
                                       "repository_intelligence/js_tree_index.py",
                                       "repository_intelligence/java_tree_index.py",
                                       "repository_intelligence/go_tree_index.py",
                                       "repository_intelligence/csharp_tree_index.py",
                                       "repository_intelligence/c_family_tree_index.py",
                                       "repository_intelligence/search.py",
                                       "repository_intelligence/source.py",
                                       "repository_intelligence/declarations.py",
                                       "repository_intelligence/structural.py",
                                       "repository_intelligence/locator.py",
                                       "repository_intelligence/inventory.py"})
            run(sys.executable, "-m", "venv", install, env=environment)
            installed_python = install / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run(installed_python, "-m", "pip", "install", "--no-index",
                "--find-links", grammar_wheels, built[0], env=environment)
            (consumer / "src").mkdir(parents=True)
            (consumer / "src/lib.rs").write_text("pub fn calculate_total(a: i32, b: i32) -> i32 { a + b }\n")
            (consumer / "src/orders.py").write_text("def calculate_total(price):\n    return price\n")
            (consumer / "src/explicit.h").write_text("fn calculate_total() {}\n")
            (consumer / "fixture.js").write_text("export function calculate_total(){ return 1; }\n")
            (consumer / "fixture.ts").write_text("export const calculate_total = (x: number) => x;\n")
            (consumer / "fixture.tsx").write_text("export const View = () => <div/>;\n")
            (consumer / "fixture.java").write_text("class C { int total(){ return 1; } }\n")
            (consumer / "fixture.go").write_text("package x\nfunc total() int { return 1 }\n")
            (consumer / "fixture.cs").write_text("class C { int Total(){ return 1; } }\n")
            (consumer / "fixture.c").write_text("int total(){ return 1; }\n")
            (consumer / "fixture.cpp").write_text("int total(){ return 1; }\n")
            script = temp / "smoke.py"
            script.write_text(
                "import json\n"
                "from pathlib import Path\n"
                "from repository_intelligence.locator import query_path\n"
                "from repository_intelligence.inventory import inventory_tree, compare_inventories\n"
                "result = query_path(Path('src'), 'calculate total')\n"
                "assert result['structural_error_count'] == 0\n"
                "single = query_path(Path('src/orders.py'), 'calculate total')\n"
                "assert single['structural']['parser']['runtime_version'] == '0.25.0'\n"
                "assert single['parser']['name'] == 'tree-sitter'\n"
                "rust = query_path(Path('src/lib.rs'), 'calculate total')\n"
                "assert rust['parser']['name'] == 'tree-sitter'\n"
                "ambiguous = query_path(Path('src/explicit.h'), 'calculate total')\n"
                "assert ambiguous['mapping_status'] == 'unsupported'\n"
                "selected = query_path(Path('src/explicit.h'), 'calculate total', language='rust')\n"
                "assert selected['matches'][0]['name'] == 'calculate_total'\n"
                "inventory = inventory_tree(Path('src'), stable=True)\n"
                "assert inventory['status'] == 'complete' and len(inventory['files']) == 2\n"
                "assert compare_inventories(inventory, inventory)['status'] == 'comparable_candidate_delta'\n"
                "assert query_path(Path('fixture.js'), 'calculate total')['matches'][0]['name'] == 'calculate_total'\n"
                "assert query_path(Path('fixture.ts'), 'calculate total')['matches'][0]['name'] == 'calculate_total'\n"
                "assert query_path(Path('fixture.tsx'), 'view')['matches'][0]['name'] == 'View'\n"
                "assert query_path(Path('fixture.java'), 'total')['matches'][0]['name'] == 'total'\n"
                "assert query_path(Path('fixture.go'), 'total')['matches'][0]['name'] == 'total'\n"
                "assert query_path(Path('fixture.cs'), 'total')['matches'][0]['name'] == 'Total'\n"
                "assert query_path(Path('fixture.c'), 'total')['matches'][0]['name'] == 'total'\n"
                "assert query_path(Path('fixture.cpp'), 'total')['matches'][0]['name'] == 'total'\n"
                "print(json.dumps(sorted(item['path'] for item in result['matches'])))\n")
            consumer_environment = {**environment, "PATH": str(install / "bin")}
            result = run(installed_python, "-I", script, cwd=consumer, env=consumer_environment)
            self.assertEqual(json.loads(result), ["src/lib.rs", "src/orders.py"])
            inventory_output = run(installed_python, "-m", "repository_intelligence.inventory",
                                   "scan", "src", "--assert-stable-materialization", "--json",
                                   cwd=consumer, env=consumer_environment)
            self.assertEqual(json.loads(inventory_output)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
