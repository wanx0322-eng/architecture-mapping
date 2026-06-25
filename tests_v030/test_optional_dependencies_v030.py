from __future__ import annotations

import importlib.abc
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BlockOptionalImports(importlib.abc.MetaPathFinder):
    blocked = {"imagehash", "numpy", "requests", "jsonschema", "PIL"}

    def find_spec(self, fullname, path, target=None):
        if fullname.split(".", 1)[0] in self.blocked:
            raise ModuleNotFoundError(fullname)
        return None


def test_prompt_compiler_imports_without_image_pipeline_dependencies():
    blocker = BlockOptionalImports()
    sys.meta_path.insert(0, blocker)
    saved = {name: sys.modules.pop(name) for name in list(sys.modules) if name.split(".", 1)[0] in blocker.blocked}
    try:
        spec = importlib.util.spec_from_file_location(
            "pipeline_v030_without_optional_dependencies",
            ROOT / "scripts/pipeline_v030.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        style = module.resolve_style("pinterest_dataset", "ecological_layered_wash", 0.7, {})
        assert style["cluster"] == "ecological_layered_wash"
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(saved)
