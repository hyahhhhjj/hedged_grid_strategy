import json

class Config:

    def __init__(self):

        self.platform: str = "binance_spot"
        self.symbol:str = "ETHUSDT"
        self.key: str = None
        self.secret: str = None
        self.min_price = 0.01
        self.min_qty = 0.0001
        self.min_trade = 10.0
        self.max_orders = 1
        self.proxy_host = ""  # proxy host
        self.proxy_port = 0  # proxy port
        self.high_bound = 0 # upper boundary of grid
        self.low_bound = 0 # lower boundary of grid
        self.grid_number = 0 # grid number
        self.hedge = True # True means hedge function would be called. You can choose turn it off
        self.hedge_mode: str = "full"# full means hedging at upper boundary, half means hedging at mid position of grid

    def loads(self, config_file=None):

        configure_dict = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configure_dict = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configure_dict:
                print("config json file error!")
                exit(0)
        self. _update(configure_dict)

    def _update(self, update_fields):

        for k, v in update_fields.items():
            setattr(self, k, v)

config = Config()
