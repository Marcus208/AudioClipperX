from setuptools import setup, find_packages

setup(
    name="audioclipperx",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "audioclipperx=audioclipperx.main:main",
        ],
    },
    install_requires=[
        "pydub",
        "ffmpeg-python",
        "PySide6",
    ],
    python_requires=">=3.11",
)
