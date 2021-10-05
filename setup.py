"""Demo project with bells and whistles."""

from ast import literal_eval
import os

from setuptools import setup, find_packages


PKGNAME = 'yamlprocessor'
URL = 'https://github.com/matthewrmshin/yamlprocessor'


# Get the long description from the README file
HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(HERE, 'README.md'), encoding='utf-8',) as handle:
    LONG_DESCRIPTION = handle.read()
with open(
    os.path.join(HERE, PKGNAME, '__init__.py'),
    encoding='utf-8',
) as handle:
    for line in handle:
        items = line.split('=', 1)
        if items[0].strip() == '__version__':
            VERSION = literal_eval(items[1].strip())
            break
    else:
        raise RuntimeError('Cannot determine package version.')


setup(
    name=PKGNAME,
    version=VERSION,
    description='Process values in YAML files',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url=URL,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development',
    ],
    keywords='demo',
    project_urls={
        'Bug Reports': f'{URL}issues',
        'Source': URL,
    },

    packages=find_packages(),
    entry_points={
        'console_scripts': [
            f'yp-data = {PKGNAME}.dataprocess:main',
            f'yp-schema = {PKGNAME}.schemaprocess:main',
        ],
    },
    include_package_data=True,

    python_requires='>=3.6, <4',
    install_requires=["jmespath", "pyyaml"],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
    extras_require={
        'dev': ['check-manifest', 'flake8'],
        'test': ['pytest', 'pytest-cov'],
    },
    zip_safe=True,
)
