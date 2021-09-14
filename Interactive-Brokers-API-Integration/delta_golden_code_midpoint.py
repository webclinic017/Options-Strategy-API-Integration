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

GlobalMinTick = 0.0
class TestApp(EWrapper, EClient):
    
    def __init__(self, broker=None):
        EClient.__init__(self, self)

        self.Portfolio_Quantity_QUOTED = 	50	
        self.TIME_HORIZON_in_Fractional_years =	0.000015
        self.Volatility_Lookback_Period_Days =	30	
        self.YEARLY_Volatility_for_Lookback_Period = 0.5 	
        self.Risk_aversion_Coefficient = 0.25
        
        self.Inventory_limit = 100
        self.Inventory_limit_innegative = -1 * self.Inventory_limit
        self.inventory_q_perorder = 50
        
        self._order_id = 0

        stocklist=pd.read_csv("C:\\delta_algo\\Mapping.csv")
        
        self.open_inventory_position_at_giventime=dict.fromkeys(stocklist['IBSymbol'],0)
        self.Unrealised_PandL_For_position_at_giventime=dict.fromkeys(stocklist['IBSymbol'],0) # For unrealised PandL - 10/23/2019
        
        self.open_order_status_end=False
        self.order_for_placing=False
        
        
    def tickReqParams(self, reqId: int, minTick:float, bboExchange:str, snapshotPermissions:int):
        super().tickReqParams(reqId, minTick, bboExchange, snapshotPermissions)
        global GlobalMinTick
        GlobalMinTick = minTick
        #print("MinTick-------:", minTick)
      
        
    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        super().tickByTickMidPoint(reqId, time, midPoint)
        
        global GlobalMinTick
        
        
        print("MidPoint Price---->", midPoint)
        print("GlobalMinTick------>", GlobalMinTick)
     
   
   
        c = self.contracts[reqId]
        
        #self.reqGlobalCancel()
        
        print("Open_inventory_position_at_giventime ---->>>>",self.open_inventory_position_at_giventime[c.symbol])        
        if(self.open_order_status_end == False):
           
            #self.reqOpenOrders() #---> Earlier for getting Position status.
            self.cancelPnLSingle(reqId)
            self.reqPnLSingle(reqId, "DU1704223", "", 380101836) # 15124833(NFLX) is contractId which is unique for every individual contract.
                                                                 # DU1704223 is the account id
                                                                 # For Calling unrealised PandL Function - 10/23/2019
            self.open_order_status_end = True
            
            
            
        if(self.open_inventory_position_at_giventime[c.symbol] == 0):
            self.order_for_placing = True
            
            
                                                     
        if(self.order_for_placing == True):
            #************************************3/Condition 1 START***********************************************# 
            if(self.open_inventory_position_at_giventime[c.symbol] == 0):
                
                Delta = self.Risk_aversion_Coefficient*midPoint*midPoint*self.YEARLY_Volatility_for_Lookback_Period*self.YEARLY_Volatility_for_Lookback_Period*self.TIME_HORIZON_in_Fractional_years
           
                RR_p = midPoint
                    
                B_p = RR_p-(Delta/2)
                B_p = B_p - (B_p % GlobalMinTick)
                B_p = round(B_p, 1)
                #B_p = round(B_p, 2)
                
               
                A_p = RR_p+(Delta/2)
                A_p = A_p - (A_p % GlobalMinTick)
                A_p = round(A_p, 1)
                #A_p = round(A_p, 2)
                
                self._send_lmt_order(self.contracts[reqId],"BUY",self.inventory_q_perorder,B_p)
                self._send_lmt_order(self.contracts[reqId],"SELL",self.inventory_q_perorder,A_p)
                
            #************************************3/Condition 1 END*************************************************#    
                
            #************************************3/Condition 2 START***********************************************# 
            elif(self.open_inventory_position_at_giventime[c.symbol] > self.Inventory_limit_innegative and\
                 self.open_inventory_position_at_giventime[c.symbol] < 0 and self.Unrealised_PandL_For_position_at_giventime[c.symbol] >3):
                
                self._send_lmt_order(self.contracts[reqId],"BUY",self.open_inventory_position_at_giventime[c.symbol],round(midPoint - (midPoint % GlobalMinTick), 1))
                
            elif(self.open_inventory_position_at_giventime[c.symbol] > 0 and\
                 self.open_inventory_position_at_giventime[c.symbol] < self.Inventory_limit and self.Unrealised_PandL_For_position_at_giventime[c.symbol] >3):
                
                self._send_lmt_order(self.contracts[reqId],"SELL",self.open_inventory_position_at_giventime[c.symbol],round(midPoint - (midPoint % GlobalMinTick), 1))
            
            #************************************3/Condition 2 END*************************************************#
            
            #************************************3/Condition 3 START***********************************************#    
            elif(self.open_inventory_position_at_giventime[c.symbol] <= self.Inventory_limit_innegative):
                self._send_lmt_order(self.contracts[reqId],"BUY",self.open_inventory_position_at_giventime[c.symbol],round(midPoint - (midPoint % GlobalMinTick), 1))
                
            elif(self.open_inventory_position_at_giventime[c.symbol] >= self.Inventory_limit):
                
                self._send_lmt_order(self.contracts[reqId],"SELL",self.open_inventory_position_at_giventime[c.symbol],round(midPoint - (midPoint % GlobalMinTick), 1))
            #************************************3/Condition 3 END*************************************************#
            
            self.order_for_placing = False  #Once order placed make it false until  pnlSingle function get the new data for position.
         
         
 
       
        #************************QUANTITY AND UNREALISED PANDL****************************#    
    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float,
                       unrealizedPnL: float, realizedPnL: float, value: float):
            super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
            
            c = self.contracts[reqId]
            
            #print("Position:-------------->>>>>>>", pos)
            print("unrealizedPnL:-------------->>>>>>>", unrealizedPnL)
            #print("realizedPnL:-------------->>>>>>>", realizedPnL)
            
            self.open_inventory_position_at_giventime[c.symbol] = pos
            self.Unrealised_PandL_For_position_at_giventime[c.symbol] = unrealizedPnL

            self.open_order_status_end = True
            self.order_for_placing = True
            
            self.reqGlobalCancel()
            
    #************************QUANTITY AND UNREALISED PANDL END************************# 
    
    #*************************************Order routing*******************************#
# =============================================================================
#     def openOrder(self, orderId: OrderId, contract: Contract, order: Order,
#                        orderState: OrderState):
#         super().openOrder(orderId, contract, order, orderState)
#         
#         sym  = contract.symbol
#         action = order.action
#         qty = order.totalQuantity
#         
#         if (orderState.status == 'Filled'):
#             
#             if action == 'BUY':
#                 self.open_inventory_position_at_giventime[sym] += qty
#             if action == 'SELL':
#                 self.open_inventory_position_at_giventime[sym] -= qty
#                 
#         else:
#             if(sym == self.ticker_symbol):
#                 self.reqGlobalCancel()    
#                 #print("Cancelled Order    @",order.lmtPrice," orderId  ",orderId)
#                 #self.cancelOrder(orderId)
#                     
#                 #self.reqGlobalCancel()
#         
# 
#                 
#     def openOrderEnd(self):
#         super().openOrderEnd()
#       
#         
#         self.open_order_status_end = True
#         self.order_for_placing=True
# =============================================================================
    
    
    def _send_lmt_order(self, contract, action, qty, lmtPrice):
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = qty
        order.lmtPrice = lmtPrice
        
        order_id = self.newOrderId()
        
       # print("Placed Order    @",lmtPrice," quantity  ",qty," symbol   ",contract.symbol," orderID  ",order_id)
  
        self.placeOrder(order_id, contract, order)

    def nextValidId(self, orderId:int):
        self._order_id = orderId
        
    def newOrderId(self):
        oid = self._order_id
        self._order_id+=1
        return oid        
    
    #*************************************Order routing*******************************#    
             

        
        
app = TestApp()
app.connect('127.0.0.1', 7497, 0)
#app.connect(socket.gethostbyname("AOC-PC"), 8100, 16)

contracts=[]
#Read the csv file for the stocklist.
stocklist=pd.read_csv("C:\\delta_algo\\Mapping.csv")


for stock in stocklist['IBSymbol']:
    print(stock)
    c = Contract()
    c.symbol = stock
    c.secType = "FUT"
    c.exchange = "MONEP"
    c.currency = "EUR"
    c.lastTradeDateOrContractMonth = "201911"
    c.multiplier = "10"
    contracts.append(c)
   
app.contracts = contracts   


    
for i in range(len(contracts)):
    #Requesting market TickByTick MipPoint data.
    app.reqTickByTickData(i, contracts[i], "MidPoint", 0, False)
    
    
for i in range(len(contracts)):
    
    app.reqMktData(i, contracts[i], '', False, False, [])
    
app.run()


