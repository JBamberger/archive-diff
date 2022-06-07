"""
Simple setup script to be able to call the install from the command line.
"""
from pathlib import Path

from setuptools import setup

about = {}
root = Path(__file__).resolve(strict=True).parent
with open(root / 'archive_diff' / '__version__.py', 'r', encoding='utf8') as f:
    exec(f.read(), about)

with open(root / 'README.md', 'r', encoding='utf8') as f:
    readme = f.read()

setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description=readme,
    long_description_content_type="text/markdown",
    author=about["__author__"],
    author_email=about["__author_email__"],
    url=about["__url__"],
    packages=["archive_diff"],
    package_data={"": ["LICENSE"]},
    package_dir={"archive_diff": "archive_diff"},
    include_package_data=True,
    python_requires=">=3.7, <4",
    license=about["__license__"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Libraries",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/JBamberger/archive-diff/issues",
        "Source": "https://github.com/JBamberger/archive-diff",
    },
    entry_points={
        'console_scripts': [
            'archive-diff = archive_diff.__main__:main'
        ]
    }
)
