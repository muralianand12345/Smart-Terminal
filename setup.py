#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name="smart-terminal",
    version="1.1.0",
    description="AI-Powered Terminal Command Generator and Executor",
    author="Murali Anand",
    author_email="smurali1607@gmail.com",
    url="https://github.com/muralianand12345/Smart-Terminal",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "st=smart_terminal.cli:run_cli",
        ],
    },
    install_requires=[
        "openai>=1.65.2",
        "pydantic>=2.10.6",
    ],
    python_requires=">=3.9",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
