"""Границы модулей: ядро не зависит от модулей, модуль не импортирует роутеры других модулей."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"


def _imports(path: Path) -> list[str]:
    return re.findall(r"^\s*(?:from|import)\s+([\w.]+)", path.read_text(encoding="utf-8"), flags=re.M)


def test_core_does_not_depend_on_modules():
    for f in (APP / "core").glob("*.py"):
        assert not any("modules" in i for i in _imports(f)), f.name


def test_modules_do_not_import_foreign_routers():
    for f in (APP / "modules").rglob("*.py"):
        own = f.parent.name
        for i in _imports(f):
            m = re.match(r"app\.modules\.(\w+)\.router", i)
            assert not m or m.group(1) == own, f"{f.relative_to(APP)} → {i}"
