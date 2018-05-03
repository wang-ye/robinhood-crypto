# Robinhood Crypto APIs
This repo provides several key APIs for Robinhood Crypto, including authorization, quotes, historicals, order placement and status.

# How to Use
1. This package goes with Python 3. I use anaconda for the python version management. This will also configure the pip accordingly.

```shell
conda create -n py36-rb python=3.6 anaconda
```

2. To install the package locally, you can run 

```shell
cd robinhood-crypto
pip install -e .
```

3. Some sample usage with the package.

```python
from robinhood_crypto_api import RobinhoodCrypto
# user/password are your Robinhood login credentials
r = RobinhoodCrypto(user, password)
# Current BTC quotes.
quote_info = r.quotes()
# Market order to buy/sell BTC
market_order_info = r.trade(
    'BTCUSD',
    price=round(float(quote_info['mark_price']) * 1.005, 2),
    quantity="0.00005",
    side="buy",
    time_in_force="gtc",
    type="market"
)
```

4. To uninstall, you can run

```shell
pip uninstall Robinhood-Crypto-API
```