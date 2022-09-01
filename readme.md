## **Hedged grid strategy**

### **对冲网格量化策略(网格策略增强)**

This strategy is developed based on Binance API. Comparing with traditional grid strategy, it has following main features which are listed
below:
1. automated setting order size in terms of realtime balance, means the longer strategy runs the bigger size it would be.
2. hedged long position, which means you do not need to worry about when price fall back through the low boundary of grid.
3. with execution algorithm. It is designed based on TWAP. I don't devote too much time in it as most of us have a relatively small capital which won't cause too much slippage.
4. fully tested

How to use it:
1. make sure your python version is 3.8x.
2. install required packages.
3. set binance_config.json correctly
4. before run this strategy, make sure you have enough balance in your spot account and perpetual account separately.(calculation can be found in documentation)
5. run binance_main.py or run start.sh(for Linux users)

## **Declaration**

 This is an open source program. And is only for study and reference. There is no backdoor is this program. But it doesn't mean you won't lose money by running this
 program as there are always risks in any kind of investment. In this case, The common types of risks can be:
 1. terminating program abruptly when it is running. This can make you hold net short position which can cause losses.
 2. losing connection with exchange server.
 3. you can always control your losses by adjusting perpetual leverage or setting stop-loss order. But there is always risk of losing money when price keep rising as the strategy is originally designed for bear market.

The types of risks are not fully listed, which means you need do your own research and make your own decision on whether using this program to help you invest. I personally won't take any responsibility for any financial losses. So please do your due diligence.