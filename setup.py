# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pinner',
    version='0.1.0',
    description='',
    long_description=long_description,
    url='',
    author='Christian Kauhaus',
    author_email='kc@flyingcircus.io',
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.5, <4',
    install_requires=['gitconfig'],
    extras_require={
        'dev': ['check-manifest'],
    },
    entry_points={
        'console_scripts': [
            'pinner=pinner.main:main',
        ],
    },
)
