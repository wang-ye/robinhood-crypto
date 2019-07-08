"""Robinhood Crypto API Utility."""
import logging
import uuid
from functools import wraps
import requests
from requests.exceptions import HTTPError
import random

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


def reauth(f):
    @wraps(f)
    def function_reauth(*args, **kwargs):
        res = None
        try:
            res = f(*args, **kwargs)
        except HTTPError as e:
            if e.response.text and ('Invalid Authorization header' in e.response.text):
                LOG.error('Experienced invalid auth header, reauth ....')
                rb = args[0]
                # Reset session and auth headers.
                acc_token = rb.get_access_token(rb.username, rb.password)
                rb.setup_for_api_call(acc_token)
                res = f(*args, **kwargs)
            else:
                raise e
        except Exception as e:
            raise e
        return res
    return function_reauth


class RobinhoodCrypto:
    PAIRS = {
        'BTCUSD': '3d961844-d360-45fc-989b-f6fca761d511',
        'ETHUSD': '76637d50-c702-4ed1-bcb5-5b0732a81f48',
        'ETCUSD': '7b577ce3-489d-4269-9408-796a0d1abb3a',
        'BCHUSD': '2f2b77c4-e426-4271-ae49-18d5cb296d3a',
        'BSVUSD': '086a8f9f-6c39-43fa-ac9f-57952f4a1ba6',
        'LTCUSD': '383280b1-ff53-43fc-9c84-f01afd0989cd',
        'DOGEUSD': '1ef78e1b-049b-4f12-90e5-555dcf2fe204'
    }

    ENDPOINTS = {
        'auth': 'https://api.robinhood.com/oauth2/token/',
        'currency_pairs': 'nummus.robinhood.com/currency_pairs',
        'quotes': 'https://api.robinhood.com/marketdata/forex/quotes/{}/',
        'historicals': 'https://api.robinhood.com/marketdata/forex/historicals/{}/?interval={}&span={}&bounds={}',
        'orders': 'https://nummus.robinhood.com/orders/',
        'order_status': 'https://nummus.robinhood.com/orders/{}',  # Order id
        'order_cancel': 'https://nummus.robinhood.com/orders/{}/cancel/',
        'nummus_accounts': 'https://nummus.robinhood.com/accounts/',
        'holdings': 'https://nummus.robinhood.com/holdings/',
        'api_accounts': 'https://api.robinhood.com/accounts/',
        'portfolios': 'https://api.robinhood.com/accounts/{}/portfolio/'
    }

    SHARED_HEADERS = {
        "accept-encoding": "gzip, deflate",
        "accept-language": "en;q=1, fr;q=0.9, de;q=0.8, ja;q=0.7, nl;q=0.6, it;q=0.5",
        "content-type": "application/json",
        "connection": "keep-alive",
        "origin": "https://robinhood.com",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
    }

    def __init__(self, username='', password='', access_token=''):
        self.username = username
        self.password = password
        self.device_token = None
        if access_token:
            _access_token = access_token
        else:
            _access_token = self.get_access_token(self.username, self.password)
        self.setup_for_api_call(_access_token)

    def setup_for_api_call(self, access_token):
        self._api_session = requests.session()
        self._api_session.headers = self.construct_api_header(access_token)
        # account id is needed for many api calls. Also cache it.
        self._account_id = self.account_id()
        self._account_number = self.account_number()

    def construct_auth_header(self):
        return {**RobinhoodCrypto.SHARED_HEADERS, **{"accept": "*/*"}}

    def construct_api_header(self, access_token):
        return {
            **RobinhoodCrypto.SHARED_HEADERS,
            **{
                'authorization': 'Bearer ' + access_token,
                "accept": "application/json",
            }
        }

    # Session request util.
    # Both the payload and response are json format.
    @reauth
    def session_request(self, url, json_payload=None, timeout=5, method='post', request_session=None):
        session = request_session if request_session else self._api_session
        try:
            resp = session.request(method, url, json=json_payload, timeout=timeout)
            # import pdb; pdb.set_trace()
            resp.raise_for_status()
        except Exception as e:
            LOG.debug('Error in session request calls. Request body {}, headers {}, content {}'.format(resp.request.body, resp.request.headers, resp.content))
            LOG.exception(e)
            raise e

        return resp.json()

    # Copied directly from https://github.com/Jamonek/Robinhood/issues/176.
    def GenerateDeviceToken(self):
        rands = []
        for i in range(0,16):
            r = random.random()
            rand = 4294967296.0 * r
            rands.append((int(rand) >> ((3 & i) << 3)) & 255)

        hexa = []
        for i in range(0,256):
            hexa.append(str(hex(i+256)).lstrip("0x").rstrip("L")[1:])

        id = ""
        for i in range(0,16):
            id += hexa[rands[i]]

            if (i == 3) or (i == 5) or (i == 7) or (i == 9):
                id += "-"
        return id

    # Autheticate user with username/password.
    # Returns: access_token for API auth.
    # Throw exception if it fails.
    def get_access_token(self, username, password, mfa_code=None):
        auth_session = requests.session()
        auth_session.headers = self.construct_auth_header()
        if not self.device_token:
            self.device_token = self.GenerateDeviceToken()
        payload = {
            'password': password,
            'username': username,
            "grant_type": "password",
            "scope": "internal",
            "client_id": "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",
            "expires_in": 86400,
            "device_token": self.device_token,
            "challenge_type": "sms"
        }

        if mfa_code:
            payload['mfa_code'] = mfa_code

        try:
            data = self.session_request(RobinhoodCrypto.ENDPOINTS['auth'], json_payload=payload, timeout=5, method='post', request_session=auth_session)
            if 'mfa_required' in data.keys():
                mfa_code = input("MFA: ")
                return self.get_access_token(username, password, mfa_code)
            access_token = data['access_token']
        except requests.exceptions.HTTPError as e:
            LOG.exception(e)
            raise LoginException()
        return access_token

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

    def accounts(self, endpoint='api_accounts'):
        assert endpoint in RobinhoodCrypto.ENDPOINTS.keys()
        url = RobinhoodCrypto.ENDPOINTS[endpoint]
        try:
            data = self.session_request(url, method='get')
        except Exception as e:
            raise e
        if 'results' in data:
            return [x for x in data['results']]
        return []

    def account_id(self):
        accounts_info = self.accounts(endpoint='nummus_accounts')
        if accounts_info:
            return accounts_info[0]['id']
        else:
            LOG.error('account cannot be retrieved')
            raise AccountNotFoundException()
        return None

    def account_number(self):
        accounts_info = self.accounts(endpoint='api_accounts')
        if accounts_info:
            return accounts_info[0]['account_number']
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

    """
    Return { 'data_points': [{ 'begins_at': '2018-05-07T00:20:00Z', 'open_price': '9636.2650', 'close_price': '9598.4300', 'high_price': '9638.0600', 'low_price': '9594.3700', 'volume': '0.0000', 'session': 'reg', 'interpolated': False }], 'bounds': '24_7', 'interval': '5minute', 'span': 'day', 'symbol': 'BTCUSD', 'id': '3d961844-d360-45fc-989b-f6fca761d511', 'open_price': None, 'open_time': None, 'previous_close_price': None, 'previous_close_time': None }
    :param pair: BTCUSD,ETHUSD
    :param interval: optional 15second,5minute,10minute,hour,day,week
    :param span: optional hour,day,year,5year,all
    :param bounds: 24_7,regular,extended,trading

    """
    def historicals(self, pair='BTCUSD', interval='5minute', span='day',  bounds='24_7'):
        symbol = RobinhoodCrypto.PAIRS[pair]
        assert symbol, 'unknown pair {}'.format(pair)
        url = RobinhoodCrypto.ENDPOINTS['historicals'].format(symbol, interval, span, bounds)
        try:
            res = self.session_request(url, method='get')
        except Exception as e:
            raise e
        return res

    """
    Returns [{
        "account_id": "fad55b1b-1142-4c84-8bb3-1e65edfa37d4",
        "cost_bases": [{
            "currency_id": "1072fc76-1862-41ab-82c2-485837590762",
            "direct_cost_basis": "0.000000000000000000",
            "direct_quantity": "0.000000000000000000",
            "id": "7d9b074c-e87e-46de-8654-0e1ef9c30459",
            "marked_cost_basis": "0.000000000000000000",
            "marked_quantity": "0.000000000000000000"
        }],
        "created_at": "2018-05-08T19:23:52.094139-04:00",
        "currency": {
            "code": "BTC",
            "id": "d674efea-e623-4396-9026-39574b92b093",
            "increment": "0.000000010000000000",
            "name": "Bitcoin",
            "type": "cryptocurrency"
        },
        "id": "76cc6887-75ee-4d6b-ad46-01a12904fb89",
        "quantity": "0.000000000000000000",
        "quantity_available": "0.000000000000000000",
        "quantity_held_for_buy": "0.000000000000000000",
        "quantity_held_for_sell": "0.000000000000000000",
        "updated_at": "2018-05-10T07:07:36.091597-04:00"
    }]
    """
    def holdings(self):
        try:
            res = self.session_request(RobinhoodCrypto.ENDPOINTS['holdings'], method='get', timeout=5)
        except Exception as e:
            raise e
        if 'results' in res:
            res = [x for x in res['results']]
            return res
        return []

    """
    Returns {
        'unwithdrawable_grants': '0.0000',
        'account': 'https://api.robinhood.com/accounts/5Q3S4FCX/',
        'excess_maintenance_with_uncleared_deposits': '0.0000',
        'url': 'https://api.robinhood.com/portfolios/5QW64535/',
        'excess_maintenance': '0.0000',
        'market_value': '0.0000',
        'withdrawable_amount': '0.0000',
        'last_core_market_value': '0.0000',
        'unwithdrawable_deposits': '0.0000',
        'extended_hours_equity': '0.0000',
        'excess_margin': '197.0700',
        'excess_margin_with_uncleared_deposits': '0.0000',
        'equity': '0.0000',
        'last_core_equity': '0.0000',
        'adjusted_equity_previous_close': '0.0000',
        'equity_previous_close': '-0.0000',
        'start_date': '2016-03-14',
        'extended_hours_market_value': '0.0000'
    }
    """
    def portfolios(self):
        url = RobinhoodCrypto.ENDPOINTS['portfolios'].format(self._account_number)
        try:
            res = self.session_request(url, method='get')
        except Exception as e:
            raise e
        return res
