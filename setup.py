from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '2.1.5'
DESCRIPTION = 'Query the ETA (Estimated Time of Arrival) of HK Bus/Minibus/MTR/Lightrail'

# Setting up
setup(
    name="hk-bus-eta",
    version=VERSION,
    author="Chun Law (chunalw)",
    author_email="<chunlaw@rocketmail.com.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=['requests'],
    keywords=['python', 'hongkong', 'eta', 'estimated time of arrival', 'kmb', 'nlb', 'mtr', 'ctb', 'minibus', 'lightrail'],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)