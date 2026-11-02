import os
import sys
from pathlib import Path

os.environ["ZPD_SKIP_DB"] = "1"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "backend" / "src"))
