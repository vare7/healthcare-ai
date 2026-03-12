"""
Config package shim under `healthcare_ai.config`.

For now this simply re-exports the existing top-level `config` package so
code can gradually migrate to `healthcare_ai.config` without breaking
existing imports like `import config` or `from config import settings`.
"""

from config import *  # noqa: F401,F403

