import sys
from pathlib import Path


def install_src_path() -> None:
    root = Path(__file__).resolve().parents[3]
    src = root / "src"
    text = str(src)
    if text not in sys.path:
        sys.path.insert(0, text)
