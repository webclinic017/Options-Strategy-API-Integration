# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 20:17:49 2019

@author: jpfra
"""

# -*- coding: utf-8 -*-
"""
Created on Fri Mar 22 10:33:05 2019

@author: RBTALGO
"""

import pandas as pd
import numpy as np
import os
import csv
import sys
import requests
import shutil
import socket
import winsound


from ibapi.client import EClient
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import *
from ibapi.tag_value import TagValue

class TestApp(EWrapper, EClient):
    
    def __init__(self, broker=None):
        EClient.__init__(self, self)
        
    def contractDetails(self, reqId, contractDetails): 
        print("ContractSymbol:", str(contractDetails.contract).split(',')[1])
        print("ContractId:", str(contractDetails.contract).split(',')[0])
        #print("ContractDetails:", contractDetails)
        
        
    def contractDetailsEnd(self, reqId):
        app.disconnect() # delete if threading and you want to stay connected

        

app = TestApp()
app.connect('127.0.0.1', 7497, 0)


contracts=[]
#Read the csv file for the stocklist.
stocklist=pd.read_csv("C:\\delta_algo\\Mapping.csv")

for stock in stocklist['IBSymbol']:
    print("Hello")

    
    c = Contract()
    c.symbol = stock
    c.secType = "FUT"
    c.exchange = "MONEP"
    c.currency = "EUR"
    c.lastTradeDateOrContractMonth = "201911"
    c.multiplier = "10"
    contracts.append(c)
   
app.contracts = contracts 
print(contracts[0])

app.reqContractDetails(4444, contracts[0]) 
    
    
app.run()