import utils
from gateway.binance_swap_http import BinanceSwapHttp,OrderSide,OrderType,OrderStatus,PositionSide
from gateway.binance_spot import BinanceSpotHttp
from trader.execution_algo import Order_Split
from utils import config
import sys


class Hedging_trader(object):

    def __init__(self):
        if config.hedge == True:
            self.http = BinanceSwapHttp(key=config.key, secret=config.secret)
            self.http_spot = BinanceSpotHttp(key=config.key, secret=config.secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
            self.default_ratio = 0.005
            self.balance_usdt = 0.0
            self.Init_balances()
            self.continue_signal = self.compare()
            if self.continue_signal == True:
                self.market_fill()
            else:
                print("out of limit")
                sys.exit(0)


    def Init_balances(self):
        data = self.http.get_account()
        assets_data = data['assets']
        for item in assets_data:
            if item['asset'] == 'USDT':
                self.balance_usdt = float(item['availableBalance'])

    def compare(self):
        data = self.http.get_bookTicker(config.symbol)
        self.bid_price = float(data["bidPrice"])
        if config.hedge_mode == "full":
            ratio = abs(config.high_bound - self.bid_price) / config.high_bound
            if ratio <= self.default_ratio:
                return True
            else:
                return False
        elif config.hedge_mode == "half":
            mid_price = 0.5 * (config.high_bound + config.low_bound)
            ratio = abs(mid_price - self.bid_price) / mid_price
            if ratio <= self.default_ratio:
                return True
            else:
                return False

    def market_fill(self):
        spot_balance = float(self.http_spot.get_account_balance_usdt())
        if config.hedge_mode == "full":
            if self.balance_usdt * 20 >= 0.5 * spot_balance:
                order_dict = {"symbol": config.symbol, "qty": utils.round_to(0.5 * spot_balance / self.bid_price, 0.001)}
                # self.http.place_order(symbol=order_dict["symbol"], side=OrderSide.SELL, positionside=PositionSide.SHORT, quantity=order_dict["qty"])
                split = Order_Split(amount=order_dict["qty"],mark_price=config.high_bound)
            else:
                print("insufficient balance")
                sys.exit(0)
        elif config.hedge_mode == "half":
            if self.balance_usdt * 20 >= spot_balance:
                order_dict = {"symbol": config.symbol, "qty": utils.round_to(spot_balance / self.bid_price, 0.001)}
                # self.http.place_order(symbol=order_dict["symbol"], side=OrderSide.SELL, positionside=PositionSide.SHORT, quantity=order_dict["qty"])
                split = Order_Split(amount=order_dict["qty"], mark_price=0.5 * (config.high_bound + config.low_bound))
            else:
                print("insufficient balance")
                sys.exit(0)
