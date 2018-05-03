from distutils.core import setup

setup(
    # Application name:
    name="Robinhood-Crypto-API",
    version="0.1.0",

    # Application author details:
    author="Ye Wang",
    author_email="happiercoder@gmail.com",

    # Packages
    packages=["robinhood_crypto_api"],
    license='MIT',

    # Include additional files into the package
    include_package_data=True,
    url="https://github.com/wang-ye/robinhood-crypto",

    description="Robinhood Crypto API",

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    # Dependent packages (distributions)
    install_requires=[
        "requests",
    ],
)
