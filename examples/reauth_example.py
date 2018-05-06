import logging
from robinhood_crypto_api import RobinhoodCrypto

logging.basicConfig(level=logging.DEBUG)


def read_credentials_from_file(file_name):
    username, password = [x.strip() for x in open(file_name).readlines()]
    return username, password


if __name__ == '__main__':
    user, password = read_credentials_from_file('../pass.txt')
    r = RobinhoodCrypto(user, password, access_token='abcdef')
    # Actual reauth happens here.
    print('quotes: {}'.format(r.quotes()))
