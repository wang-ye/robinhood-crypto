"""Robinhood Crypto API Utility."""
import logging
import uuid
import requests

LOG = logging.getLogger(__name__)


class RobinhoodCryptoException(Exception):
    pass


class LoginException(RobinhoodCryptoException):
    pass


class TokenExchangeException(RobinhoodCryptoException):
    pass


class TradeException(RobinhoodCryptoException):
    pass


class QuoteException(RobinhoodCryptoException):
    pass


class AccountNotFoundException(RobinhoodCryptoException):
    pass


class RobinhoodCrypto:
    PAIRS = {
        'BTCUSD': '3d961844-d360-45fc-989b-f6fca761d511',
        'ETHUSD': '76637d50-c702-4ed1-bcb5-5b0732a81f48',
    }

    ENDPOINTS = {
        'login': 'https://api.robinhood.com/oauth2/token/',
        'currency_pairs': 'nummus.robinhood.com/currency_pairs',
        'quotes': 'https://api.robinhood.com/marketdata/forex/quotes/{}/',
        'historicals': 'https://api.robinhood.com/marketdata/forex/historicals/{}/',
        'orders': 'https://nummus.robinhood.com/orders/',
        'order_status': 'https://nummus.robinhood.com/orders/{}',  # Order id
        'order_cancel': 'https://nummus.robinhood.com/orders/{}/cancel/',
        'accounts': "https://nummus.robinhood.com/accounts",
    }

    def __init__(self, username, password):
        self._session = requests.session()
        self._session.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en;q=1, fr;q=0.9, de;q=0.8, ja;q=0.7, nl;q=0.6, it;q=0.5",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Origin": "https://robinhood.com",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
        }
        self.login(username, password)
        self._account_id = self.account_id()

    def login(self, username, password):
        access_token = self.get_access_token(username, password)
        self.setup_header_for_json_request(access_token)

    # Session request util.
    # Both the payload and response are json format.
    def session_request(self, url, json_payload=None, timeout=5, method='post'):
        try:
            req = self._session.request(method, url, json=json_payload, timeout=timeout)
            req.raise_for_status()
        except Exception as e:
            LOG.error('Error in session_request calls. Request body {}, headers {}'.format(req.request.body, req.request.headers))
            LOG.exception(e)
            raise e

        return req.json()

    # Autheticate user with username/password.
    # Returns: access_token for API auth.
    # Throw exception if it fails.
    def get_access_token(self, username, password):
        payload = {
            'password': password,
            'username': username,
            "grant_type": "password",
            "scope": "internal",
            "client_id": "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",
            "expires_in": 86400,
        }

        try:
            data = self.session_request(RobinhoodCrypto.ENDPOINTS['login'], json_payload=payload, timeout=5, method='post')
            access_token = data['access_token']
        except requests.exceptions.HTTPError as e:
            LOG.exception(e)
            raise LoginException()

        return access_token

    def setup_header_for_json_request(self, access_token):
        self._session.headers['Authorization'] = 'Bearer ' + access_token
        self._session.headers['Content-Type'] = 'application/json'
        self._session.headers['Accept'] = 'application/json'

    # Return: dict
    # {'ask_price': '8836.3300', 'bid_price': '8801.0500', 'mark_price': '8818.6900', 'high_price': '9064.6400', 'low_price': '8779.9599', 'open_price': '8847.2400', 'symbol': 'BTCUSD', 'id': '3d961844-d360-45fc-989b-f6fca761d511', 'volume': '380373.1898'}
    def quotes(self, pair='BTCUSD'):
        symbol = RobinhoodCrypto.PAIRS[pair]
        assert symbol, 'unknown pair {}'.format(pair)
        url = RobinhoodCrypto.ENDPOINTS['quotes'].format(symbol)

        try:
            data = self.session_request(url, method='get')
        except requests.exceptions.HTTPError:
            raise QuoteException()
        return data

    def accounts(self):
        url = RobinhoodCrypto.ENDPOINTS['accounts']
        try:
            data = self.session_request(url, method='get')
        except Exception as e:
            raise e
        if 'results' in data:
            return [x for x in data['results']]
        return []

    def account_id(self):
        accounts_info = self.accounts()
        if accounts_info:
            return accounts_info[0]['id']
        else:
            LOG.error('account cannot be retrieved')
            raise AccountNotFoundException()
        return None

    # return:
    # dict in format
    # {
    #     "account_id":"abcd",
    #     "cancel_url":"https://nummus.robinhood.com/orders/{order_id}/cancel/",
    #     "created_at":"2018-04-22T14:07:37.103809-04:00",
    #     "cumulative_quantity":"0.000000000000000000",
    #     "currency_pair_id":"3d961844-d360-45fc-989b-f6fca761d511",
    #     "executions":[],
    #     "id":"efgh",
    #     "last_transaction_at":null,
    #     "price":"9028.670000000000000000",
    #     "quantity":"0.000111860000000000",
    #     "ref_id":"ijk",
    #     "side":"buy",
    #     "state":"unconfirmed",
    #     "time_in_force":"gtc",
    #     "type":"market",
    #     "updated_at":"2018-04-22T14:07:37.250180-04:00"
    # }
    def trade(self, pair, **kwargs):
        assert pair in RobinhoodCrypto.PAIRS.keys(), 'pair {} is not in {}.'.format(pair, RobinhoodCrypto.PAIRS.keys())
        set(kwargs.keys()) == ['price', 'quantity', 'side', 'time_in_force', 'type']
        payload = {
            **{
                'account_id': self._account_id,
                'currency_pair_id': RobinhoodCrypto.PAIRS[pair],
                'ref_id': str(uuid.uuid4()),
            },
            **kwargs
        }
        try:
            res = self.session_request(RobinhoodCrypto.ENDPOINTS['orders'], json_payload=payload, method='post', timeout=5)
        except Exception as e:
            raise TradeException()
        return res

    # TODO(ye): implement pagination.
    def trade_history(self):
        try:
            res = self.session_request(RobinhoodCrypto.ENDPOINTS['orders'], method='get', timeout=5)
        except Exception as e:
            raise TradeException()
        return res

    # return value:
    # {
    # 'account_id': 'abcd', 'cancel_url': None, 'created_at': '2018-04-22T14:07:37.103809-04:00', 'cumulative_quantity': '0.000111860000000000', 'currency_pair_id': '3d961844-d360-45fc-989b-f6fca761d511', 'executions': [{'effective_price': '8948.500000000000000000', 'id': 'hijk', 'quantity': '0.000111860000000000', 'timestamp': '2018-04-22T14:07:37.329000-04:00'}], 'id': 'order_id', 'last_transaction_at': '2018-04-22T14:07:37.329000-04:00', 'price': '9028.670000000000000000', 'quantity': '0.000111860000000000', 'ref_id': 'ref_id', 'side': 'buy', 'state': 'filled', 'time_in_force': 'gtc', 'type': 'market', 'updated_at': '2018-04-22T14:07:38.956584-04:00'
    # }
    def order_status(self, order_id):
        url = RobinhoodCrypto.ENDPOINTS['order_status'].format(order_id)
        try:
            res = self.session_request(url, method='get')
        except Exception as e:
            raise e
        return res

    def order_cancel(self, order_id):
        url = RobinhoodCrypto.ENDPOINTS['order_cancel'].format(order_id)
        try:
            res = self.session_request(url, method='post')
        except Exception as e:
            raise e
        return res
