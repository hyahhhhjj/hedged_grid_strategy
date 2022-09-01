import time

import utils
from gateway.binance_swap_http import BinanceSwapHttp,OrderSide,OrderType,OrderStatus,PositionSide
from utils import config
import sys

class Order_Split(object):
    def __init__(self, amount: float, mark_price: float):
        self.http = BinanceSwapHttp(key=config.key, secret=config.secret)
        self.amount = amount
        self.mark_price = mark_price
        self.split_fill()
    def split_fill(self):
        while True:
            data = self.http.get_bookTicker(config.symbol)
            bid_price = float(data["bidPrice"])
            bid_qty = float(data["bidQty"])
            ratio = abs(self.mark_price - bid_price) / self.mark_price
            if ratio <= 0.01:
                if self.amount > bid_qty:
                    try:
                        self.http.place_order(symbol=config.symbol, side=OrderSide.SELL, positionside=PositionSide.SHORT, quantity=utils.round_to(bid_qty, 0.001))
                    except:
                        pass
                    self.amount -= bid_qty
                else:
                    try:
                        self.http.place_order(symbol=config.symbol, side=OrderSide.SELL, positionside=PositionSide.SHORT, quantity=utils.round_to(self.amount, 0.001))
                    except:
                        pass
                    break
            else:
                print("out of limit")
                sys.exit(0)
            time.sleep(2)


