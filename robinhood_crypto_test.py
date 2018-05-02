import getpass
from robinhood_crypto_api import Robinhood


def read_credentials():
    username = input("Username: ")
    password = getpass.getpass()
    return username, password


if __name__ == '__main__':
    user, password = read_credentials()
    r = Robinhood(user, password)
    quote_info = r.quotes()
    print('quotes: {}'.format(quote_info))
    print('account: {}'.format(r.account_id()))
    print('most recent trade history: {}'.format(r.trade_history()['results'][:5]))

    # Market order
    market_order_info = r.trade(
        'BTCUSD',
        price=round(float(quote_info['mark_price']) * 1.005, 2),
        quantity="0.00005",
        side="buy",
        time_in_force="gtc",
        type="market"
    )
    order_id = market_order_info['id']
    print('market order {} status: {}'.format(order_id, r.order_status(order_id)))

    # Limit orders
    limit_order_info = r.trade(
        'BTCUSD',
        # price=1.00,
        price=round(float(quote_info['mark_price']) * 0.8, 2),
        quantity="0.00005",
        side="buy",
        time_in_force="gtc",
        type="limit"
    )
    order_id = limit_order_info['id']
    print('limit order {} status: {}'.format(order_id, r.order_status(order_id)))
    print('canceling limit order {}: {}'.format(order_id, r.order_cancel(order_id)))
