"""Compatibility shim for editable installs with older pip/setuptools."""

from setuptools import find_packages, setup


setup(
    name="hierarchical-codebase-graph",
    version="0.1.0",
    description="Deterministic CLI for hierarchical codebase graph artifacts",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"hierarchical_graph": ["schema.json"]},
    entry_points={"console_scripts": ["hgraph=hierarchical_graph.cli:entrypoint"]},
)

