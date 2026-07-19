from setuptools import setup, find_packages

setup(
    name="laboratory-evidence",
    version="0.1.0",
    description="Laboratory Evidence Protocol",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "jsonschema>=4.0.0"
    ],
    extras_require={
        "dev": [
            "pytest",
            "hypothesis"
        ]
    }
)
