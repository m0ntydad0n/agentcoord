"""Setup configuration for agentcoord package."""

from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="agentcoord",
    version="0.1.0",
    description="Redis-based multi-agent coordination system",
    author="m0ntydad0n",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "agentcoord=agentcoord.cli:cli",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
