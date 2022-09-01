import time
from gateway import BinanceSpotHttp, OrderStatus, OrderType, OrderSide
from utils import config
from utils import utility, round_to
from enum import Enum
import logging
import numpy as np
from datetime import datetime
import copy

class GridTrader(object):

    def __init__(self):
        self.http_client = BinanceSpotHttp(key=config.key, secret=config.secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        self.grid_scale, self.grid_list = self.grid_generator()
        print("------------------------------")
        print(f"grid_list: {self.grid_list}")
        self.unsettled_grid = config.grid_number
        print("------------------------------")
        print(f"grid_scale: {self.grid_scale}")
        self.amount = 0.0
        self.buy_orders = []
        self.sell_orders = []

    def grid_generator(self):
        grid_list_local = []
        high_bound = config.high_bound
        low_bound = config.low_bound
        grid_number = config.grid_number
        grid_scale = (high_bound - low_bound) / grid_number
        for i in range(grid_number + 1):
            grid_list_local.append(round_to((high_bound - i * grid_scale), float(config.min_price)))
        return grid_scale,grid_list_local

    def sell_price_generator(self, filled_price: float) -> float:
        return round_to((filled_price + self.grid_scale), float(config.min_price))

    def sell_qty_generator(self, filled_qty: float) -> float:
        return round_to((filled_qty), float(config.min_qty))

    def buy_price_generator(self, filled_price: float) -> float:
        if filled_price > self.grid_list[config.grid_number]:
            return round_to((filled_price - self.grid_scale), float(config.min_price))
        else:
            return 0

    def buy_qty_generator(self, next_buy_price: float) -> float:
        usdt_balance = self.http_client.get_account_balance_usdt()
        quantity_usdt = float(usdt_balance) / float(self.unsettled_grid)
        buy_qty = round_to((quantity_usdt / next_buy_price), float(config.min_qty))
        new_qty = self.trade_check(next_buy_price,buy_qty)
        return new_qty
    # this function is used in case amount is to small, you can delete it as well
    def trade_check(self, price: float, amount: float) -> float:
        for qty in np.arange(amount,round_to(0.01,float(config.min_qty)),config.min_qty):
            qty = round_to(qty,float(config.min_qty))
            if qty * price >= config.min_trade:
                return qty
        return amount

    def buy_price_generator_F(self, bid_price) -> float:
        for index in range(len(self.grid_list)):
            if bid_price < self.grid_list[index] and bid_price >= self.grid_list[index+1]:
                return self.grid_list[index+1]

    def get_latest_price(self):
        data = self.http_client.get_price(config.symbol)
        return float(data['price'])

    def get_bid_ask_price(self):
        tick_data = self.http_client.get_ticker(config.symbol)
        return float(tick_data["bidPrice"]), float(tick_data["askPrice"])

    def grid_trader(self):
        order_dict = {"order-id": "0", "symbol": config.symbol, "amount": 0.0, "price": 0.0}
        last_price = self.get_latest_price()
        bid_price, ask_price = self.get_bid_ask_price()
        print(f"trade price: {last_price}")

        self.buy_orders.sort(key=lambda x: float(x['price']), reverse=True)
        self.sell_orders.sort(key=lambda x: float(x['price']), reverse=True)
        print(f"buy orders: {self.buy_orders}")
        print("------------------------------")
        print(f"sell orders: {self.sell_orders}")

        buy_delete_orders = []
        sell_delete_orders = []

        new_buy_order = {}
        new_sell_order = {}

        buy_price = 0

        # buy order logic
        if self.buy_orders:
            for buy_order in self.buy_orders:
                check_order = self.http_client.get_order(config.symbol,buy_order["order-id"])
                if check_order:
                    if check_order["status"] == OrderStatus.CANCELED.value:
                        print("------------------------------")
                        print(f"buy order CANCELED")
                        self.buy_orders.remove(buy_order)
                        new_buy_order = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT,float(check_order.get("origQty")), float(check_order.get("price")))
                        if new_buy_order:
                            order_dict["order-id"] = str(new_buy_order["orderId"])
                            order_dict["symbol"] = config.symbol
                            order_dict["amount"] = float(check_order.get("origQty"))
                            order_dict["price"] = float(check_order.get("price"))
                            self.buy_orders.append(order_dict.copy())
                        print(f"buy order status was canceled: {check_order.get('status')} and new buy order was set{order_dict}")
                    elif check_order["status"] == OrderStatus.FILLED.value:
                        print("------------------------------")
                        print(f"buy orders FILLED")
                        logging.info(f"time: {datetime.now()}, price: {check_order.get('price')}, qty: {check_order.get('origQty')}")
                        # current position check
                        self.amount = self.amount + float(check_order.get('origQty'))
                        print("------------------------------")
                        print(f"current_position: {self.amount}")
                        self.unsettled_grid = self.unsettled_grid - 1
                        self.buy_orders.remove(buy_order)

                        sell_price = self.sell_price_generator(float(check_order.get("price")))
                        sell_qty = self.sell_qty_generator(float(check_order.get("origQty")))
                        print("------------------------------")
                        print(f"sell_price: {sell_price}")
                        print("------------------------------")
                        print(f"sell_qty: {sell_qty}")

                        if 0 < sell_price < bid_price:
                            # in case of volatility
                            sell_price = round_to(bid_price, float(config.min_price))

                        new_sell_order = self.http_client.place_order(config.symbol, OrderSide.SELL, OrderType.LIMIT, sell_qty, sell_price)

                        if new_sell_order:
                            order_dict["order-id"] = str(new_sell_order["orderId"])
                            order_dict["symbol"] = config.symbol
                            order_dict["amount"] = sell_qty
                            order_dict["price"] = sell_price
                            self.sell_orders.append(order_dict.copy())

                        buy_price = self.buy_price_generator(float(check_order.get("price")))
                        buy_qty = self.buy_qty_generator(buy_price)

                        if 0 < ask_price < buy_price:
                            # in case of volatility
                            buy_price = round_to(ask_price, float(config.min_price))

                        if buy_price != 0:
                            new_buy_order = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT,
                                                                      buy_qty, buy_price)

                        if new_buy_order:
                            order_dict["order-id"] = str(new_buy_order["orderId"])
                            order_dict["symbol"] = config.symbol
                            order_dict["amount"] = buy_qty
                            order_dict["price"] = buy_price
                            self.buy_orders.append(order_dict.copy())
        else:
            buy_price = self.buy_price_generator_F(bid_price)
            buy_qty = self.buy_qty_generator(buy_price)
            print(f"First buy price: {buy_price}")
            print(f"First buy qty: {buy_qty}")

            if buy_price != 0:
                new_buy_order = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT,
                                                                      buy_qty, buy_price)
            if new_buy_order:
                order_dict["order-id"] = str(new_buy_order["orderId"])
                order_dict["symbol"] = config.symbol
                order_dict["amount"] = buy_qty
                order_dict["price"] = buy_price
                self.buy_orders.append(order_dict.copy())

        # sell order logic
        for sell_order in self.sell_orders:
            check_order = self.http_client.get_order(config.symbol,sell_order["order-id"])
            if check_order:
                if check_order.get("status") == OrderStatus.CANCELED.value:
                    print("------------------------------")
                    print(f"sell_order_CANCELED")
                    self.sell_orders.remove(sell_order)
                    new_sell_order = self.http_client.place_order(config.symbol, OrderSide.SELL, OrderType.LIMIT, float(check_order.get("origQty")), float(check_order.get("price")))
                    if new_sell_order:
                        order_dict["order-id"] = str(new_sell_order["orderId"])
                        order_dict["symbol"] = config.symbol
                        order_dict["amount"] = float(check_order.get("origQty"))
                        order_dict["price"] = float(check_order.get("price"))
                        self.sell_orders.append(order_dict.copy())
                    print(f"sell order status was canceled: {check_order.get('state')} and new sell order was set{order_dict}")
                elif check_order.get("status") == OrderStatus.FILLED.value:
                    print("------------------------------")
                    print(f"sell_order_FILLED")
                    logging.info(f"time: {datetime.now()}, price: {check_order.get('price')}, qty: {check_order.get('origQty')}")
                    # current position check
                    self.amount = self.amount - float(check_order.get('origQty'))
                    print("------------------------------")
                    print(f"current_position: {self.amount}")
                    self.unsettled_grid = self.unsettled_grid + 1
                    buy_delete_orders.append(self.buy_orders[-1].copy())
                    self.buy_orders.remove(self.buy_orders[-1])
                    self.sell_orders.remove(sell_order)

                    buy_price = self.buy_price_generator(float(check_order.get("price")))
                    buy_qty = self.buy_qty_generator(buy_price)

                    if 0 < ask_price < buy_price:
                        buy_price = round_to(bid_price, float(config.min_price))

                    if buy_price != 0:
                        new_buy_order = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT,
                                                                      buy_qty, buy_price)

                    if new_buy_order:
                        order_dict["order-id"] = str(new_buy_order["orderId"])
                        order_dict["symbol"] = config.symbol
                        order_dict["amount"] = buy_qty
                        order_dict["price"] = buy_price
                        self.buy_orders.append(order_dict.copy())

        # regenerate buy order
        if len(self.sell_orders) == 0:
            for buy_cancel in self.buy_orders:
                buy_price = self.buy_price_generator_F(bid_price)
                print("-----------")
                print(f"buy_cancel_price:{buy_cancel['price']}")
                if abs(buy_cancel["price"] - buy_price) >= self.grid_scale:
                    data = self.http_client.cancel_order(config.symbol, int(buy_cancel["order-id"]))
                    data2 = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT, buy_cancel["amount"], buy_price)
                    if data["code"] == "200":
                        self.buy_orders.remove(buy_cancel)
                    if data2:
                        order_dict["order-id"] = str(data2["orderId"])
                        order_dict["symbol"] = config.symbol
                        order_dict["amount"] = buy_cancel["amount"]
                        order_dict["price"] = buy_price
                        self.buy_orders.append(order_dict.copy())

        # order need to be deleted
        while True:
            if buy_delete_orders:
                for delete_buy in buy_delete_orders:
                    data = self.http_client.cancel_order(config.symbol,int(delete_buy["order-id"]))
                    if data["code"] != "200":
                        break
                    else:
                        buy_delete_orders.remove(delete_buy)
            else:
                break
            time.sleep(0.2)

