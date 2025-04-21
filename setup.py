from setuptools import setup, find_packages
import sys
import re

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

with open("README.md", "r", encoding="utf-8") as f:
    readme_text = f.read()
    
VERSIONFILE = 'seavoyage/_version.py'
verstrline = open(VERSIONFILE, encoding="utf-8").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError(f"Unable to find version string in {VERSIONFILE}.")

major_version, minor_version = sys.version_info[:2]
if not (major_version == 3 and 7 <= minor_version <= 13):
    sys.stderr.write("Sorry, only Python 3.9 - 3.13 are "
                     "supported at this time.\n")
    exit(1)

setup(
    name="seavoyage",
    version=verstr,
    description="An improved version of searoute package for calculating the shortest sea route between two points on Earth.",
    license="Apache 2.0",
    keywords="sea route, shortest path, graph, geojson, networkx",
    author="Byeonggong Hwang",
    author_email="bk22106@gmail.com",
    url="https://github.com/a22106/seavoyage",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    package_data={
        'seavoyage': [
            'data/geojson/marnet/*',
            'data/shorelines/**/*',
            'data/samples/*',
            'data/ports/*',
        ],
    },
    include_package_data=True,
)
