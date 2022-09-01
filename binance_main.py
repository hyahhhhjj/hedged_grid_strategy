import time
import logging
from trader.binance_grid_trader import GridTrader
from trader.hedging_trader import Hedging_trader
from utils import config
from threading import Thread,Lock
from apscheduler.schedulers.background import BackgroundScheduler,BlockingScheduler

format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=format, filename='binance_grid_trader_log.txt')
logger = logging.getLogger('binance')

if __name__ == '__main__':
    config.loads('./binance_config.json')
    hedge = Hedging_trader()
    trader = GridTrader()
    scheduler = BlockingScheduler()
    scheduler.add_job(func=trader.grid_trader, trigger="interval", seconds=5)
    scheduler.start()
    # while True:
    #     trader.grid_trader()
    #     time.sleep(5)

