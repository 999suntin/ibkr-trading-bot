#Imports
#
import ibapi
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import ta
import numpy as np
import pandas as pd
import pytz
import math
from datetime import datetime, timedelta
import threading
import time

#Vars
orderId = 1


#Class for connnecting to IBKR
class IBApi(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
    #Get historical data (if bot starts late) / Historical Backtest Data
    def historicalData(self, reqId, bar):
        try: 
            bot.on_bar_update(reqId, bar, False)
        except Exception as e:
            print(e)

    #On Realtime Bar after historical data finishes
    def historicalDataUpdate(self, reqId, bar):
        try: 
            bot.on_bar_update(reqId, bar, True)
        except Exception as e:
            print(e)
    #On Historical data ends
    def historicalDataEnd(self, reqId, start, end):
        print("ReqID : below")
        print(reqId)
        

    #Get next order ID
    def nextValidId(self, nextorderId):
        global orderId
        orderId = nextorderId

    #Listen for realtimeBars
    def realtimeBar(self, reqId, time, open_, high, low, close, volume, wap, count):
        super().reqRealTimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        try:
            bot.on_bar_update(reqId, time, open_, high, low, close, volume, wap, count)
        except Exception as e:
            print(e)
        
        def error(self, id, errorCode, errorMsg):
            print(errorCode)
            print(errorMsg)

   


#Bar Object
class Bar:
    open = 0
    low = 0
    high = 0
    close = 0 
    volume = 0
    date = datetime.now()
    def __init__(self):
        self.open = 0
        self.low = 0
        self.high = 0
        self.close = 0
        self.volume = 0
        self.date = datetime.now()



#Bot Logic
class Bot:
    ib = None
    barsize = 1
    currentBar = Bar()
    bars = []
    reqId = 1
    global orderId
    ema1Period = 9
    ema2Period = 21
    symbol = ""
    initialbartime = datetime.now().astimezone(pytz.timezone("America/New_York"))



    def __init__(self):
        #Connect to IBKR on init
        self.ib = IBApi()
        # 4001 = Gateway port  -- 7497 = TWS port
        self.ib.connect("127.0.0.1", 7497, 1)
    
        #threading
        ib_thread = threading.Thread(target=self.run_loop, daemon=True)
        ib_thread.start()
        time.sleep(1)

        currentBar = Bar()

        #Get Symbol/Ticker
        self.symbol = input("Enter the symbol/ticker you want to trade: ")

        #Get bar size
        #Valid bar sizes are: _ secs, 1 min, _ mins, 1 hour, _ hours, 1 day, 1 week, 1 month
        self.barsize = input("Enter the barsize you want to trade in minutes : ")
        text = " min"
        if (int(self.barsize) > 1 and int(self.barsize) < 60):
            text = " mins"
        elif (int(self.barsize) == 60):
            self.barsize = self.barsize / 60
            text = " hour"
        elif (int(self.barsize) >= 120 and int(self.barsize) < 1440):
            self.barsize = self.barsize / 60
            text = " hours"
        elif (int(self.barsize) == 1440):
            self.barsize = 1
            text = " day"
        elif (int(self.barsize) > 1440):
            self.barsize = self.barsize / 1440
            text = " days"


        
        queryTime = (datetime.now().astimezone(pytz.timezone("America/New_York"))-timedelta(days=1)).replace(hour=16,minute=0,second=0,microsecond=0).strftime("%Y%m%d %H:%M:%S")
        print("Querytime complete")


        #Create contract/Stock object to store stock info
        contract = Contract()
        contract.symbol = self.symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        #Request Market Data
        #self.ib.reqRealTimeBars(0, contract, 3600, "MIDPOINT", 1, []) # 1 = Regular Trading Hours - 0 = all trading hours
        self.ib.reqHistoricalData(self.reqId,contract,"","2 D",str(self.barsize)+text,"MIDPOINT",0,1,True,[])

    #threading cont
    #Listen to socket in seperate thread
    def run_loop(self):
        self.ib.run()

    # Order setup
    def marketOrder(self, action, quantity):
        #Create contract/Stock object to store stock info
        contract = Contract()
        contract.symbol = self.symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity

        return order




    #Pass realtime bar data back to object
    def on_bar_update(self, reqId, bar, realtime):
        global orderId
        #Historical Data to catch up
        if (realtime == False):
            self.bars.append(bar)
        else:
            bartime = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S").astimezone(pytz.timezone("America/New_York"))
            #print("getting historical bar data")
            minutes_diff = (bartime-self.initialbartime).total_seconds() / 60.0
            self.currentBar.date = bartime
            lastBar = self.bars[len(self.bars)-1]
            #On Bar Close
            if (minutes_diff > 0 and math.floor(minutes_diff) % int(self.barsize) == 0):
                self.initialbartime = bartime
                #Entry 
                closes = []
                for bar in self.bars:
                    closes.append(bar.close)
                
                #first EMA (9 period ema)
                self.close_array = pd.Series(np.asarray(closes))
                self.ema1 = ta.trend.ema_indicator(self.close_array, self.ema1Period, True)
                print("Current EMA9 : " + str(self.ema1[len(self.ema1)-1]))
                print("Previous EMA9 : " + str(self.ema1[len(self.ema1)-2]))
                #second EMA (21 period ema)
                self.close_array = pd.Series(np.asarray(closes))
                self.ema2 = ta.trend.ema_indicator(self.close_array, self.ema2Period, True)
                print("Current EMA21 : " + str(self.ema2[len(self.ema2)-1]))
                print("Previous EMA21 : " + str(self.ema2[len(self.ema2)-2]))

                print("Criteria check")
                

                #Criteria check
                if (str(self.ema1[len(self.ema1)-1]) > str(self.ema2[len(self.ema2)-1]) and str(self.ema2[len(self.ema2)-2]) >= str(self.ema1[len(self.ema1)-2])):
                    print("BUY ORDER EXECUTING")
                    #Order Buy
                    quantity = 1
                    mktOrder = self.marketOrder("BUY", quantity)
                    contract = Contract()
                    contract.symbol = self.symbol.upper()
                    contract.secType = "STK"
                    contract.exchange = "SMART"
                    contract.currency = "USD"
                    print(orderId)
                    self.ib.placeOrder(orderId, contract, mktOrder)
                    orderId += 1
                    
                
                if (str(self.ema2[len(self.ema2)-1]) > str(self.ema1[len(self.ema1)-1]) and str(self.ema2[len(self.ema2)-2]) < str(self.ema1[len(self.ema1)-2])):
                    print("SELL ORDER EXECUTING")
                    #Order Sell
                    quantity = 1
                    mktOrder = self.marketOrder("SELL", quantity)
                    contract = Contract()
                    contract.symbol = self.symbol.upper()
                    contract.secType = "STK"
                    contract.exchange = "SMART"
                    contract.currency = "USD"
                    print(orderId)
                    self.ib.placeOrder(orderId, contract, mktOrder)
                    orderId += 1
                
                
                

                #Bar closed append 
                self.currentBar.close = bar.close
                if (self.currentBar.date != lastBar.date):
                    print("New bar")
                    self.bars.append(self.currentBar)
                self.currentBar.open = bar.open
        
        #build realtime bar
        if (self.currentBar.open == 0):
            self.currentBar.open = bar.open
        if (self.currentBar.high == 0 or bar.high > self.currentBar.high):
            self.currentBar.high = bar.high
        if (self.currentBar.low == 0 or bar.low > self.currentBar.low):
            self.currentBar.low = bar.low
                
                        


#Start bot
bot = Bot()


