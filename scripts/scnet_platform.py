"""Small cross-platform helpers for local level-A and quick-build execution."""
import os
from pathlib import Path
import shutil


def find_bash() -> str:
    """Return a usable bash executable; prefer Git Bash on Windows over WSL."""
    candidates = []
    if os.name == "nt":
        for variable in ("ProgramFiles", "ProgramW6432"):
            root = os.environ.get(variable)
            if root:
                candidates.append(Path(root) / "Git" / "bin" / "bash.exe")
        candidates.extend([shutil.which("bash.exe"), shutil.which("bash")])
    else:
        candidates.append(shutil.which("bash"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise FileNotFoundError(
        "bash is required for level-A/quick-build; install Git Bash on Windows"
    )


def is_executable(path: Path) -> bool:
    """Treat native executable suffixes as executable on Windows."""
    if os.name == "nt":
        return path.suffix.lower() in {".exe", ".bat", ".cmd", ".com"}
    return os.access(str(path), os.X_OK)
