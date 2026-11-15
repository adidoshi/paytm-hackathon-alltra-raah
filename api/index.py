import sys
from pathlib import Path

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [str(_repo_root), str(_this_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if not __package__:
    __package__ = "api"

from api.main import app

app = app
