"""
Wrapper entrypoint for demo mode.

This delegates to the existing root-level `run_demo.py` script so that
`healthcare_ai.demo.run_demo` can be referenced without breaking current
CLI usage (`python run_demo.py`).
"""

from run_demo import *  # noqa: F401,F403

