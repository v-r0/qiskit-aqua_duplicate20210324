# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, 2021.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import setuptools
import inspect
import sys
import os

long_description = """<a href="https://qiskit.org/aqua" rel=nofollow>Qiskit Aqua</a> is an extensible,
 modular, open-source library of quantum computing algorithms.
 Researchers can experiment with Aqua algorithms, on near-term quantum devices and simulators,
 and can also get involved by contributing new algorithms and algorithm-supporting objects,
 such as optimizers and variational forms.
 Qiskit Aqua also contains application domain support in the form of the chemistry, finance,
 machine learning and optimization modules to experiment with real-world applications to quantum computing."""

requirements = [
    "qiskit-terra>=0.16.0",
    "qiskit-ignis>=0.4.0",
    "scipy>=1.4",
    "sympy>=1.3",
    "numpy>=1.17",
    "psutil>=5",
    "scikit-learn>=0.20.0",
    "dlx",
    "docplex; sys_platform != 'darwin'",
    "docplex==2.15.194; sys_platform == 'darwin'",
    "fastdtw",
    "setuptools>=40.1.0",
    "h5py",
    "pandas",
    "quandl",
    "yfinance",
    "retworkx>=0.7.0",
    "dataclasses; python_version < '3.7'"
]

if not hasattr(setuptools, 'find_namespace_packages') or not inspect.ismethod(setuptools.find_namespace_packages):
    print("Your setuptools version:'{}' does not support PEP 420 (find_namespace_packages). "
          "Upgrade it to version >='40.1.0' and repeat install.".format(setuptools.__version__))
    sys.exit(1)

VERSION_PATH = os.path.join(os.path.dirname(__file__), "qiskit", "aqua", "VERSION.txt")
with open(VERSION_PATH, "r") as version_file:
    VERSION = version_file.read().strip()

setuptools.setup(
    name='qiskit-aqua',
    version=VERSION,
    description='Qiskit Aqua: An extensible library of quantum computing algorithms',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/Qiskit/qiskit-aqua',
    author='Qiskit Aqua Development Team',
    author_email='hello@qiskit.org',
    license='Apache-2.0',
    classifiers=(
        "Environment :: Console",
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering"
    ),
    keywords='qiskit sdk quantum aqua',
    packages=setuptools.find_namespace_packages(include=['qiskit.*']),
    install_requires=requirements,
    include_package_data=True,
    python_requires=">=3.6",
    extras_require={
        'torch': ["torch"],
        'cplex': ["cplex; python_version < '3.9'"],
        'cvx': ['cvxpy>1.0.0,!=1.1.0,!=1.1.1,!=1.1.2,!=1.1.8'],
        'pyscf': ["pyscf; sys_platform != 'win32'"],
        'skquant': ["scikit-quant"],
    },
    zip_safe=False
)
