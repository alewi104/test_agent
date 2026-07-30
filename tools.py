# tools.py

import subprocess
from pathlib import Path
from langchain_core.tools import tool

TEST_OUTPUT_DIR = Path("tests_output").resolve()
TEST_OUTPUT_DIR.mkdir(exist_ok=True)


@tool
def read_file(path: str, project_root:str) -> str:
    """Read and return the contents of a file at the given path, relative to project_root."""
    try:
        full_path = Path(project_root) / path
        return full_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found at {full_path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def get_project_structure(path: str, max_depth: int = 3) -> str:
    """Return a tree-like listing of the project's directory structure, skipping common noise directories like node_modules and .git."""
    ignore = {"node_modules", ".git", "__pycache__", "venv", ".venv", ".github", "public", "dist"}
    root = Path(path)
    lines = []

    def walk(current: Path, depth: int, prefix: str = ""):
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name))
        except PermissionError:
            return
        for entry in entries:
            if entry.name in ignore:
                continue
            lines.append(f"{prefix}{entry.name}")
            if entry.is_dir():
                walk(entry, depth + 1, prefix + "  ")

    walk(root, 0)
    return "\n".join(lines) if lines else f"No files found at {path}"


@tool
def write_test_file(filename: str, content: str, overwrite: bool = False) -> str:
    """Write a Python pytest-Playwright test file (filename must end in .py) into the sandboxed tests_output directory. Fails if the file already exists unless overwrite is True."""
    if not filename.endswith(".py"):
        return "Error: filename must end in .py — tests must be Python (pytest-playwright), not JavaScript."
    
    target = (TEST_OUTPUT_DIR / filename).resolve()

    # keep writes inside TEST_OUTPUT_DIR
    if TEST_OUTPUT_DIR not in target.parents and target != TEST_OUTPUT_DIR:
        return "Error: path escapes the sandboxed output directory."

    if target.exists() and not overwrite:
        return f"Error: {filename} already exists. Set overwrite=True to replace it."

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} chars to {target}"


@tool
def run_pytest(filename: str, timeout: int = 60) -> str:
    """Run a Playwright test file via pytest and return pass/fail output, including any error details."""
    target = (TEST_OUTPUT_DIR / filename).resolve()
    if TEST_OUTPUT_DIR not in target.parents and target != TEST_OUTPUT_DIR:
        return "Error: path escapes the sandboxed output directory."

    try:
        result = subprocess.run(
            ["pytest", str(target), "-v"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        status = "PASSED" if result.returncode == 0 else "FAILED"
        return f"{status}\n{output}"
    except subprocess.TimeoutExpired:
        return f"Error: test run exceeded {timeout}s timeout."