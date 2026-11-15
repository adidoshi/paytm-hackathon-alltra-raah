import importlib.util
import sys
from pathlib import Path

_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
for _p in [str(_repo_root), str(_this_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if "api" not in sys.modules:
    _init_file = _this_dir / "__init__.py"
    if not _init_file.exists():
        _init_file.touch()
    _spec = importlib.util.spec_from_file_location("api", str(_init_file), submodule_search_locations=[str(_this_dir)])
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["api"] = _mod
        _spec.loader.exec_module(_mod)

if not __package__:
    __package__ = "api"

from api.main import app

app = app
