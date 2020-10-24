# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='credentialparser',
    version='1.1.2',

    description='A Credential Parser',
    long_description=long_description,

    url='https://github.com/zachhanson94/credentialparser',

    author='Zach Hanson',
    author_email='zachhanson94@gmail.com',

    license='ISC',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Programming Language :: Python :: 3.7',
    ],

    entry_points = {
        'console_scripts': ['credparser=CredentialParser.cli.credparser:main']
    },

    keywords='credparser',

    packages=find_packages(),

    install_requires=['argparse', 'psycopg2-binary', 'humanize'],
)
