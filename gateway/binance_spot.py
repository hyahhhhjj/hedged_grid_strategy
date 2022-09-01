"""
spot API
for more info, please check out with https://binance-docs.github.io/apidocs/spot/
"""
import requests
import time
import hmac
import hashlib
from enum import Enum
from threading import Thread, Lock


class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    PENDING_CANCEL = "PENDING_CANCEL"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"


class RequestMethod(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'


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


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class BinanceSpotHttp(object):

    def __init__(self, key=None, secret=None, host=None, proxy_host=None, proxy_port=None, timeout=5, try_counts=5):
        self.key = key
        self.secret = secret
        self.host = host if host else "https://api.binance.com"
        self.host_sign = "api.binance.com"
        self.recv_window = 5000
        self.timeout = timeout
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.order_count_lock = Lock()
        self.order_count = 1_000_000
        self.try_counts = try_counts

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
        return requests.request(req_method.value, url=url, headers=headers, timeout=self.timeout,
                                proxies=self.proxies).json()

    def get_server_time(self):
        path = '/api/v3/time'
        return self.request(req_method=RequestMethod.GET, path=path)

    def _timestamp(self):
        return int(time.time() * 1000)

    def get_account_info(self):
        path = "/fapi/v1/account"
        params = {"timestamp": self._timestamp()}
        return self.request(RequestMethod.GET, path, params, verify=True)

    def get_exchange_info(self):
        path = '/api/v3/exchangeInfo'
        return self.request(req_method=RequestMethod.GET, path=path)

    def get_depth(self, symbol: str, depth=5, type="step1"):
        depths = [5, 10, 20, 50, 100, 500, 1000, 5000]
        if depth not in depths:
            depth = 5

        path = "/api/v3/depth"
        query_dict = {"symbol": symbol,
                      "limit": depth
                      }

        return self.request(RequestMethod.GET, path, query_dict)

    def get_kline(self, symbol, period: Interval, start_time=None, end_time=None, depth=500, max_try_time=10):
        path = "/api/v3/klines"

        query_dict = {
            "symbol": symbol,
            "interval": period.value,
            "limit": depth
        }

        if start_time:
            query_dict['startTime'] = start_time

        if end_time:
            query_dict['endTime'] = end_time

        for i in range(max_try_time):
            data = self.request(RequestMethod.GET, path, query_dict)
            if isinstance(data, list) and len(data):
                return data

    def get_price(self, symbol: str):
        path = "/api/v3/ticker/price"
        query_dict = {"symbol": symbol}
        return self.request(RequestMethod.GET, path, query_dict)

    def get_ticker(self, symbol):
        path = "/api/v3/ticker/bookTicker"
        query_dict = {"symbol": symbol}
        return self.request(RequestMethod.GET, path, query_dict)

    ########################### the following request is for private data ########################
    def get_client_order_id(self):
        """
        generate the client_order_id for user.
        :return: new client order id
        """
        with self.order_count_lock:
            self.order_count += 1
            return "x-cLbi5uMH" + str(self._timestamp()) + str(self.order_count)

    def _sign(self, params):

        requery_string = self.build_parameters(params)
        hexdigest = hmac.new(self.secret.encode('utf8'), requery_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return requery_string + '&signature=' + str(hexdigest)

    def place_order(self, symbol: str, side: OrderSide, order_type: OrderType, quantity=0, price=0, time_inforce="GTC",
                    recvWindow=5000, stop_price=0, client_order_id=None):

        path = '/api/v3/order'
        if client_order_id is None:
            client_order_id = self.get_client_order_id()

        params = {
            "symbol": symbol,
            "side": side.value,
            "type": order_type.value,
            "quantity": quantity,
            "price": price,
            "recvWindow": recvWindow,
            "timestamp": self._timestamp(),
            "newClientOrderId": client_order_id
        }

        if order_type == OrderType.LIMIT:
            params['timeInForce'] = time_inforce

        if order_type == OrderType.MARKET:
            if params.get('price'):
                del params['price']

        if order_type == OrderType.STOP:
            if stop_price > 0:
                params["stopPrice"] = stop_price
            else:
                raise ValueError("stopPrice must greater than 0")
        return self.request(RequestMethod.POST, path=path, requery_dict=params, verify=True)

    def get_order(self, symbol, order_id=None):
        path = "/api/v3/order"
        query_dict = {"symbol": symbol, "timestamp": self._timestamp()}
        if order_id:
            query_dict["orderId"] = int(order_id)

        return self.request(RequestMethod.GET, path, query_dict, verify=True)

    def cancel_order(self, symbol, order_id=None):
        path = "/api/v3/order"
        params = {"symbol": symbol, "timestamp": self._timestamp()}
        if order_id:
            params["orderId"] = order_id

        return self.request(RequestMethod.DELETE, path, params, verify=True)

    def get_open_orders(self, symbol=None):
        path = "/api/v3/openOrders"

        params = {"timestamp": self._timestamp()}
        if symbol:
            params["symbol"] = symbol

        return self.request(RequestMethod.GET, path, params, verify=True)

    def get_balance(self):
        path = "/sapi/v1/capital/config/getall"
        params = {"timestamp": self._timestamp()}

        return self.request(RequestMethod.GET, path=path, requery_dict=params, verify=True)

    def get_account_balance_usdt(self):
        data = self.get_balance()
        for item in data:
            if item["coin"] == "USDT":
                return float(item["free"])




