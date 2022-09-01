'''
perpetual API
for more info, please check out with https://binance-docs.github.io/apidocs/futures/
'''
import requests
import time
import hmac
import hashlib
from enum import Enum
from threading import Thread, Lock

lock = Lock()

class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(Enum):
    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"

class Interval(Enum):
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    HOUR_1 = '1h'
    HOUR_2 = '2h'
    HOUR_4 = '4h'
    HOUR_6 = '6h'
    HOUR_8 = '8h'
    HOUR_12 = '12h'
    DAY_1 = '1d'
    DAY_3 = '3d'
    WEEK_1 = '1w'
    MONTH_1 = '1M'

class RequestMethod(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'

class BinanceSwapHttp(object):
    def __init__(self, key=None, secret=None, host=None, proxy_host=None, proxy_port=None, timeout=0.3, try_counts=5):
        self.key = key
        self.secret = secret
        self.host = host if host else "https://fapi.binance.com"
        self.host_sign = "fapi.binance.com"
        self.recv_window = 5000
        self.timeout = timeout
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.order_count_lock = Lock()
        self.order_count = 1_000_000
        self.try_counts = try_counts

        self.client_order_id = ""
        self.long_id = ""
        self.short_id = ""

    @property
    def proxies(self):
        if self.proxy_port and self.proxy_host:
            proxy = f"http://{self.proxy_host}:{self.proxy_port}"
            return {"http": proxy, "https": proxy}
        return None

    def build_parameters(self, params: dict):
        keys = list(params.keys())
        keys.sort()
        return '&'.join([f"{key}={params[key]}" for key in params.keys()])

    def request(self, req_method: RequestMethod, path: str, requery_dict=None, verify=False):
        url = self.host + path
        if verify:
            query_str = self._sign(requery_dict)
            url += '?' + query_str
        elif requery_dict:
            url += '?' + self.build_parameters(requery_dict)
        headers = {"X-MBX-APIKEY": self.key}
        return requests.request(req_method.value, url=url, headers=headers, timeout=self.timeout, proxies=self.proxies).json()

    def _sign(self, params):
        requery_string = self.build_parameters(params)
        hexdigest = hmac.new(self.secret.encode('utf8'), requery_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return requery_string + '&signature=' + str(hexdigest)

    def _timestamp(self):
        return int(time.time() * 1000)

    def get_client_order_id(self):
        with self.order_count_lock:
            self.order_count += 1
            return "x-cLbi5uMH" + str(self._timestamp()) + str(self.order_count)

    def place_order(self, symbol: str, side: OrderSide, positionside: PositionSide, ordertype: OrderType = OrderType.MARKET, quantity=0, price=0, stop_price=0, time_inforce="GTC", recvWindow=5000, client_order_id=None):

        path = '/fapi/v1/order'
        if client_order_id is None:
            client_order_id = self.get_client_order_id()
        self.client_order_id = client_order_id
        if positionside == PositionSide.LONG:
            self.long_id = client_order_id
        elif positionside == PositionSide.SHORT:
            self.short_id = client_order_id

        params = {
            "symbol": symbol,
            "side": side.value,
            "positionSide": positionside.value,
            "type": ordertype.value,
            "quantity": quantity,
            "price": price,
            "recvWindow": recvWindow,
            "timestamp": self._timestamp(),
            "newClientOrderId": client_order_id
        }

        if ordertype == OrderType.LIMIT:
            params['timeInForce'] = time_inforce

        elif ordertype == OrderType.MARKET:
            params.pop("price")

        elif ordertype == OrderType.STOP_MARKET:
            params.pop("price")
            params["stopPrice"] = stop_price

        elif ordertype == OrderType.TAKE_PROFIT_MARKET:
            params.pop("price")
            params["stopPrice"] = stop_price

        return self.request(RequestMethod.POST, path=path, requery_dict=params, verify=True)

    def get_order(self, symbol, order_id=None):
        path = "/fapi/v1/order"
        query_dict = {"symbol": symbol, "timestamp": self._timestamp()}
        if order_id:
            query_dict["orderId"] = int(order_id)

        return self.request(RequestMethod.GET, path, query_dict, verify=True)

    def cancel_order(self, symbol, order_id=None):
        path = "/fapi/v1/order"
        params = {"symbol": symbol, "timestamp": self._timestamp()}
        if order_id:
            params["orderId"] = order_id

        return self.request(RequestMethod.DELETE, path, params, verify=True)

    def get_order_by_cid(self, symbol, origClientOrderId=None):
        path = "/fapi/v1/order"
        query_dict = {"symbol": symbol, "timestamp": self._timestamp()}
        if origClientOrderId:
            query_dict["origClientOrderId"] = origClientOrderId

        return self.request(RequestMethod.GET, path, query_dict, verify=True)

    def cancel_order_by_cid(self, symbol, origClientOrderId=None):
        path = "/fapi/v1/order"
        params = {"symbol": symbol, "timestamp": self._timestamp()}
        if origClientOrderId:
            params["origClientOrderId"] = origClientOrderId

        return self.request(RequestMethod.DELETE, path, params, verify=True)

    def cancel_order_by_id(self, symbol, orderId: int = 0):
        path = "/fapi/v1/order"
        params = {"symbol": symbol, "timestamp": self._timestamp()}
        if orderId:
            params["orderId"] = orderId

        return self.request(RequestMethod.DELETE, path, params, verify=True)

    def cancel_all_open_order(self, symbol):
        path = "/fapi/v1/allOpenOrders"
        params = {"symbol": symbol,"recvWindow":self.recv_window, "timestamp": self._timestamp()}
        return self.request(RequestMethod.DELETE, path, params, verify=True)

    def get_account(self):
        path = "/fapi/v2/account"
        params = {"timestamp": self._timestamp(),
                  "recvWindow": self.recv_window}
        return self.request(RequestMethod.GET, path, params, verify=True)

    def get_bookTicker(self, symbol: str):
        path = "/fapi/v1/ticker/bookTicker"
        params = {"symbol": symbol}
        return self.request(RequestMethod.GET, path, params, verify=False)

    def get_markprice(self, symbol: str):
        path = "/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        return self.request(RequestMethod.GET, path, params, verify=False)

    def get_depth(self, symbol: str, depth=5):
        depths = (5, 10, 20, 50, 100, 500, 1000)
        if depth not in depths:
            depth = 5
        path = "/fapi/v1/depth"

        query_dict = {"symbol": symbol,
                      "limit": depth}

        return self.request(RequestMethod.GET, path, query_dict)

    def get_exchange_info(self):
        path = "/fapi/v1/exchangeInfo"
        return self.request(RequestMethod.GET, path)

    # functions below are used for order status monitoring(Websocket), you can always delete them.
    def generate_listen_key(self):
        path = "/fapi/v1/listenKey"
        return self.request(RequestMethod.POST, path, requery_dict=None, verify=False)

    def extend_listen_key(self):
        path = "/fapi/v1/listenKey"
        return self.request(RequestMethod.PUT, path,requery_dict=None, verify=False)

    def delete_listen_key(self):
        path = "/fapi/v1/listenKey"
        return self.request(RequestMethod.DELETE, path,requery_dict=None, verify = False)

