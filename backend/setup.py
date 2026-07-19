from setuptools import find_packages, setup


setup(
    name="merge-marshal-api",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.115,<1",
        "uvicorn>=0.30,<1",
    ],
    extras_require={"test": ["httpx>=0.27,<1"]},
)
