"""
ZeroDB Local - Complete local development environment for ZeroDB
"""
from setuptools import setup, find_packages
from setuptools.command.install import install
import os
import subprocess

class PostInstallCommand(install):
    """Post-installation script to set up Docker services"""
    def run(self):
        install.run(self)
        print("\n" + "="*60)
        print("ZeroDB Local installed successfully!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Run: zerodb init")
        print("  2. Services will start at:")
        print("     - Dashboard: http://localhost:3000")
        print("     - API: http://localhost:8000")
        print("="*60 + "\n")

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="zerodb-local",
    version="1.0.0",
    author="AINative Studio",
    author_email="hello@ainative.studio",
    description="Complete local development environment for ZeroDB with Docker Compose",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/relycapital/core",
    project_urls={
        "Bug Tracker": "https://github.com/relycapital/core/issues",
        "Documentation": "https://www.ainative.studio/docs",
        "Source Code": "https://github.com/relycapital/core/tree/main/zerodb-local",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords="zerodb database vector embeddings docker local development",
    packages=find_packages(include=['cli', 'cli.*']),
    include_package_data=True,
    package_data={
        '': [
            'docker-compose.yml',
            '.env.local.example',
            'api/**/*',
            'dashboard/**/*',
            'embeddings/**/*',
            'scripts/**/*',
            'docs/**/*',
        ],
    },
    python_requires=">=3.9",
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
        "requests>=2.31.0",
        "httpx>=0.24.0",
        "pyyaml>=6.0",
        "click>=8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "zerodb=cli.zerodb_main:app",
            "zerodb-local=cli.zerodb_main:app",
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
    },
)
