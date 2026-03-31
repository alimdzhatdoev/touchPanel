from __future__ import annotations

import sys
from pathlib import Path

# Репозиторий в PYTHONPATH при прямом вызове pytest из подкаталога
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
