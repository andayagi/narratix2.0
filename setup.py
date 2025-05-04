"""Setup file for the Narratix package."""

from setuptools import setup, find_packages

setup(
    name="narratix",
    version="2.0.0",
    description="Transform text into dramatized audio experiences using AI",
    author="Narratix Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "anthropic>=0.50.0",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "requests>=2.31.0",
        "tabulate>=0.9.0",
        "tqdm>=4.66.1",
        "pydub>=0.25.1",
        "aiohttp>=3.9.0",
        "psutil>=5.9.5",
        "tiktoken>=0.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "isort>=5.12.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "narratix=narratix.main:main",
        ],
    },
    python_requires=">=3.13",
) 