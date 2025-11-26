#!/usr/bin/env python3
"""Setup script for openstack-lb-treeview"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="openstack-lb-treeview",
    # version is automatically derived from git tags via setuptools-scm
    use_scm_version={
        "write_to": "openstack_lb_treeview/_version.py",
        "version_scheme": "release-branch-semver",
        "local_scheme": "no-local-version",
    },
    setup_requires=["setuptools-scm[toml]>=6.2"],
    description="Display a tree view of OpenStack loadbalancers, pools, and members",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Samuel Alfageme Sainz",
    author_email="samuel@alfage.me",
    url="https://github.com/SamuAlfageme/openstack-lb-treeview",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "openstack-lb-treeview=openstack_lb_treeview.lb_treeview:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
    ],
    keywords="openstack loadbalancer octavia treeview",
)

