"""
Backend package shim under `healthcare_ai.backend`.

For now this simply re-exports the existing top-level `backend` package so
code can gradually migrate to `healthcare_ai.backend` without breaking
existing imports like `import backend`.
"""

from backend import *  # noqa: F401,F403

