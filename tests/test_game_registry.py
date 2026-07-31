import importlib.util
from pathlib import Path
import sys


MODULE = Path(__file__).parents[1] / "game_registry.py"
spec = importlib.util.spec_from_file_location("game_registry", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_session_lifecycle():
    registry = module.GameSessionRegistry()
    game_id = registry.start("123", "guess", "Guess", timeout=60)
    assert registry.snapshot()[0]["group_id"] == "123"
    assert registry.touch(game_id)
    assert registry.finish(game_id)
    assert registry.snapshot() == []
