# Robinhood Crypto APIs
This repo provides several key APIs for Robinhood Crypto, including authorization, quotes, historicals, order placement and status.

# How to Use
1. Install Python 3. I use anaconda for the python version management.

```shell
conda create -n py36-rb python=3.6 anaconda
```

2. Install the necessary packages.

```shell
pip install -r requirements.txt 
```

3. You can now copy the file ``robinhood_crypto_api.py`` in your own project, and run ``from robinhood_crypto_api import Robinhood``. I will make it package later it can be installed directly. 
