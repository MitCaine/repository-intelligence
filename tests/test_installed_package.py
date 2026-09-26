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
        expected_versions = {"tree-sitter": "0.25.0", "tree-sitter-python": "0.25.0",
                             "tree-sitter-rust": "0.24.2", "tree-sitter-javascript": "0.25.0",
                             "tree-sitter-typescript": "0.23.2", "tree-sitter-java": "0.23.5",
                             "tree-sitter-go": "0.25.0", "tree-sitter-c-sharp": "0.23.5",
                             "tree-sitter-c": "0.24.2", "tree-sitter-cpp": "0.23.4"}
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
            expected_modules = {f"repository_intelligence/{path.name}" for path in
                                (ROOT / "src/repository_intelligence").glob("*.py")}
            self.assertEqual(modules, expected_modules)
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
                "from importlib.metadata import version\n"
                "from pathlib import Path\n"
                "from repository_intelligence.locator import query_path\n"
                "from repository_intelligence.inventory import inventory_tree, compare_inventories\n"
                "from repository_intelligence.rust_semantic import resolve_definition\n"
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
                f"expected_versions = {expected_versions!r}\n"
                "assert {name: version(name) for name in expected_versions} == expected_versions\n"
                "grammar_probes = {'src/orders.py': ('total', 'tree-sitter-python'), "
                "'src/lib.rs': ('total', 'tree-sitter-rust'), "
                "'fixture.js': ('total', 'tree-sitter-javascript'), "
                "'fixture.ts': ('total', 'tree-sitter-typescript'), "
                "'fixture.tsx': ('view', 'tree-sitter-typescript'), "
                "'fixture.java': ('total', 'tree-sitter-java'), "
                "'fixture.go': ('total', 'tree-sitter-go'), "
                "'fixture.cs': ('total', 'tree-sitter-c-sharp'), "
                "'fixture.c': ('total', 'tree-sitter-c'), "
                "'fixture.cpp': ('total', 'tree-sitter-cpp')}\n"
                "for path, (term, distribution) in grammar_probes.items():\n"
                "    parser = query_path(Path(path), term)['structural']['parser']\n"
                "    assert parser['runtime_version'] == expected_versions['tree-sitter']\n"
                "    assert parser['grammar_version'] == expected_versions[distribution]\n"
                "    assert parser['adapter_version'] == 10\n"
                "polyglot = inventory_tree(Path('.'), stable=True)\n"
                "assert polyglot['status'] == 'complete'\n"
                "assert {f['path'] for f in polyglot['files']} == "
                "{'src/lib.rs', 'src/orders.py', 'fixture.js', 'fixture.ts', 'fixture.tsx', "
                "'fixture.java', 'fixture.go', 'fixture.cs', 'fixture.c', 'fixture.cpp'}\n"
                "Path('fixture.js').write_text('export function calculate_total(){ return 2; }\\n')\n"
                "changed = inventory_tree(Path('.'), stable=True)\n"
                "delta = compare_inventories(polyglot, changed)\n"
                "assert delta['status'] == 'comparable_candidate_delta'\n"
                "assert [f['path'] for f in delta['file_changes']['modified']] == ['fixture.js']\n"
                "assert len(delta['declaration_changes']['modified']) == 1\n"
                "print(json.dumps({'matches': sorted(item['path'] for item in result['matches']), "
                "'versions': {name: version(name) for name in expected_versions}}))\n")
            consumer_environment = {**environment, "PATH": str(install / "bin")}
            result = run(installed_python, "-I", script, cwd=consumer, env=consumer_environment)
            payload = json.loads(result)
            self.assertEqual(payload["matches"], ["src/lib.rs", "src/orders.py"])
            self.assertEqual(payload["versions"], expected_versions)
            inventory_output = run(installed_python, "-m", "repository_intelligence.inventory",
                                   "scan", "src", "--assert-stable-materialization", "--json",
                                   cwd=consumer, env=consumer_environment)
            self.assertEqual(json.loads(inventory_output)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
