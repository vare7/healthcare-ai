"""
Wrapper module for the Streamlit UI.

For now, this simply imports the root-level `streamlit_app` module so that
`healthcare_ai.ui.streamlit_app` can be used as a stable import path without
changing existing behavior or entrypoints.
"""

# Importing this module executes the Streamlit app defined at the project root.
import streamlit_app  # noqa: F401

