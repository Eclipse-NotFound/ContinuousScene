"""Independent copyPixels normal-stamp component using the frozen-input runner."""
from pathlib import Path
import importlib.util
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
parent_path = HERE.parent / 'decal-stamp-tolerance/run.py'
spec = importlib.util.spec_from_file_location('copy_pixels_component_base', parent_path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Only this in-memory module instance is redirected. The original runner and
# its r1/r2 evidence remain byte-for-byte unchanged.
runner.HERE = HERE
runner.HELPER = HERE / 'tests/SceneDecalStampProof.as'
runner.VERSION = 'decal-stamp-copy-pixels-runner-1'
original_inputs = runner.runner_inputs


def runner_inputs():
    return dict(original_inputs(), **{str(Path(__file__)): runner.r.sha(Path(__file__))})


runner.runner_inputs = runner_inputs
runner.base.runner_inputs = runner_inputs
if __name__ == '__main__':
    runner.main()
