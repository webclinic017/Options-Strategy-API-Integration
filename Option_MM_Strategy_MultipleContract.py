# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 15:14:05 2020
@author: RBT ALGO SYSTEMS LLP
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
import logging 
from datetime import datetime
import pytz # $ pip install pytz

tz='Asia/Kolkata'

from ibapi.client import EClient
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import *
from ibapi.tag_value import TagValue


def SetupLogger():

    
    logging.basicConfig(filename="C:\\JP_Project_NFLX\\LogFile.log", 
                            format='%(asctime)s %(message)s', 
                            filemode='w') #Create and configure logger 

    logger=logging.getLogger() #Creating an object 

    console = logging.StreamHandler()
    logger.setLevel(logging.INFO) #Setting the threshold of logger to DEBUG
    logger.addHandler(console)
    

class TestApp(EWrapper, EClient):
   
    def __init__(self, broker=None):
        EClient.__init__(self, self)
        
        self.Call_Option_Quantity = 1
        self.Put_Option_Quantity = 1
        self.Underlying_Quantity = 100


        self.C_L = 2 # To store Limits on call positions
        
        self.P_L = 2 # To store Limits on put positions
        
        self.S_L = 200 # To store Limits on stock positions

        self._order_id = 0
        stocklist=pd.read_csv("C:\\JP_Project_NFLX\\Mapping_MICHELIN_jp.csv")
        
        self.stockcontract_id=pd.read_csv("C:\\JP_Project_NFLX\\Mapping_MICHELIN_jp.csv")
      
        self.minimumTick = dict.fromkeys(stocklist['Serial_Nu'], 0) # Minimum Tick for each contract
        
        self.N_P = dict.fromkeys(stocklist['Serial_Nu'], 0) # Number of PUT(K,T) in Position
        self.N_C = dict.fromkeys(stocklist['Serial_Nu'], 0) # Number of Call(K,T) in Position
        self.N_S = dict.fromkeys(stocklist['Serial_Nu'], 0) # Number of stock in Position
        self.UPL = dict.fromkeys(stocklist['Serial_Nu'], 0) # Unrealized PnL of the complete position (stock+Option)
        self.RPL = dict.fromkeys(stocklist['Serial_Nu'], 0) # Daily Realized PnL
         
        self.Gamma_Call = dict.fromkeys(stocklist['Serial_Nu'], 0)   # To store Gamma value
        self.IV_Call = dict.fromkeys(stocklist['Serial_Nu'], 0) # To store Implied Volatility
        
        self.Gamma_Put = dict.fromkeys(stocklist['Serial_Nu'], 0)   # To store Gamma value
        self.IV_Put = dict.fromkeys(stocklist['Serial_Nu'], 0) # To store Implied Volatility

        self.S = dict.fromkeys(stocklist['Serial_Nu'], 0)  # S(mid) underlying stock mid price 
        self.Call_Ask_Price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Call ask price
        self.Call_Bid_Price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Call bid price
        

        self.Put_Ask_Price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Put ask price
        self.Put_Bid_Price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Put bid price
        
        self.Stock_Ask_price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Stock ask price
        self.Stock_Bid_price = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Stock bid price
       
        
        self.D_C = dict.fromkeys(stocklist['Serial_Nu'], 0)  # Delta(Call(K,T))
        self.D_P= dict.fromkeys(stocklist['Serial_Nu'], 0)  # Delta(Put(K,T))
        self.BDELTA= dict.fromkeys(stocklist['Serial_Nu'], 0) # for storing BDELTA for Delta hedge

        self.open_order_status_end = False
        self.order_for_placing = True
        
        
    #**************************MinTick start******************************#
    def tickReqParams(self, reqId: int, minTick:float, bboExchange:str, snapshotPermissions:int):
        super().tickReqParams(reqId, minTick, bboExchange, snapshotPermissions)
       
        self.minimumTick[reqId] = minTick
     
        
    #*****************************MinTick end*****************************#
    
    
    #**************************Tick by tick midpoint start******************************#
    
    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        super().tickByTickMidPoint(reqId, time, midPoint)

        logging.info("MidPoint Price of Underlying Stock--->" + str(midPoint))
        self.S[reqId] = midPoint
            
        
    #*****************************Tick by tick midpoint end*****************************#
    
    
    #****************************Option Greeks  start*****************************# 
    
    def tickOptionComputation(self, reqId: TickerId, tickType, impliedVol: float, delta: float, optPrice: float, pvDividend: float, gamma: float, vega: float, theta: float, undPrice: float):
        super().tickOptionComputation(reqId, tickType, impliedVol, delta, optPrice, pvDividend, gamma, vega, theta, undPrice)
        
        c = self.contracts[reqId]
        
        if tickType == 13:
            
            if c.right == 'C':
                logging.info("Gamma for CALL----->" + str(gamma))
                self.Gamma_Call[reqId] =  gamma 
             
            if c.right == 'P':
                logging.info("Gamma for PUT----->" + str(gamma))
                self.Gamma_Put[reqId] =  gamma 
           
            
            if c.right == 'C':
                logging.info("IV for CALL----->" + str(impliedVol))
                self.IV_Call[reqId] =  impliedVol 
             
            if c.right == 'P':
                logging.info("IV for PUT----->" + str(impliedVol))
                self.IV_Put[reqId] =  impliedVol



            if c.right == 'C':
                logging.info("Delta for CALL----->" + str(delta))
                self.D_C[reqId] = delta
                
            if c.right == 'P':
                logging.info("Delta for PUT----->" + str(delta))
                self.D_P[reqId] = delta
                
        
        
    #*****************************Option Greeks  end******************************# 
    
    
    
    #****************************Tick Price(BID/ASK/LTP) start*****************************#     
        
    def tickPrice(self, reqId: TickerId , tickType, price: float, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        
        c = self.contracts[reqId]
        
        self.reqGlobalCancel()
        
        logging.info("Total_Unrealised_PandL for stock + option---->>>>" + str(sum(self.UPL.values())))
        logging.info("Total_Realised_PandL for stock + option---->>>>" + str(sum(self.RPL.values())))
    
        df_Current_Contract = self.stockcontract_id.loc[(self.stockcontract_id['IBSymbol'] == c.symbol)]
        df_Current_Contract = df_Current_Contract.reset_index(drop = True)

        # Call Bid Price and Call Ask Price
        if c.right == 'C':

            
            if tickType == 2:
                logging.info("Call_Ask_Price---->>>>" + str(price))
                self.Call_Ask_Price[reqId] = price
                
            elif tickType == 1:
                logging.info("Call_Bid_Price---->>>>" + str(price))
                self.Call_Bid_Price[reqId] = price
      
        
                
        # Put Bid Price and Put Ask Price    
        elif c.right == 'P':

            
            if tickType == 2:
                logging.info("Put_Ask_Price---->>>>" + str(price))
                self.Put_Ask_Price[reqId] = price
                
            elif tickType == 1:
                logging.info("Put_Bid_Price---->>>>" + str(price))
                self.Put_Bid_Price[reqId] = price
                
        else:
            
            if tickType == 2:
                self.Stock_Ask_price[int(df_Current_Contract['Serial_Nu'].iloc[2])] = price
                
            elif tickType == 1:
                self.Stock_Bid_price[int(df_Current_Contract['Serial_Nu'].iloc[2])] = price
                
        if(self.Stock_Ask_price[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and self.Stock_Bid_price[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0):
            
            self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] = round((self.Stock_Ask_price[int(df_Current_Contract['Serial_Nu'].iloc[2])] + self.Stock_Bid_price[int(df_Current_Contract['Serial_Nu'].iloc[2])])/2,2)
            
                
#############################################################################################################
             
        if(self.open_order_status_end == False): # This if condition executed once for getting Unrealised P and L regularly.


            for i in range(len(self.stockcontract_id)):

                self.cancelPnLSingle(int(self.stockcontract_id['Serial_Nu'].iloc[i]))
                self.reqPnLSingle(int(self.stockcontract_id['Serial_Nu'].iloc[i]), "DU1704223", "", int(self.stockcontract_id['Contract_Id'].iloc[i])) # 15124833(NFLX) is contractId which is unique for every individual contract.
                                                                                              # DU1704223 is the account id
                                                                                              # For Calling unrealised PandL Function - 10/23/2019
            self.open_order_status_end = True

##############################################################################################################            
            
        if(self.order_for_placing == True):
           
            # When the position limit is not exceeded
                       
            if abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) < self.C_L or abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) < self.P_L  or  abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) < self.S_L :
                
                # Computing New Prices  

                 D_Call = 0.5 * self.Gamma_Call[int(df_Current_Contract['Serial_Nu'].iloc[0])] * (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]*self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) * (self.IV_Call[int(df_Current_Contract['Serial_Nu'].iloc[0])]*self.IV_Call[int(df_Current_Contract['Serial_Nu'].iloc[0])])
                 D_Put = 0.5 * self.Gamma_Put[int(df_Current_Contract['Serial_Nu'].iloc[1])] * (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]*self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) * (self.IV_Put[int(df_Current_Contract['Serial_Nu'].iloc[1])]*self.IV_Put[int(df_Current_Contract['Serial_Nu'].iloc[1])])
                  
                 Call_a = 0.5 * (self.Call_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])] + self.Call_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])]) + D_Call
                 Call_b = 0.5 * (self.Call_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])] + self.Call_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])]) - D_Call
                
                 
                 Put_a = 0.5 * (self.Put_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])] + self.Put_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])]) + D_Put
                 Put_b = 0.5 * (self.Put_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])] + self.Put_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])]) - D_Put
                 
                 
                     
                 if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])] != 0 and abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) < self.C_L and Call_b != 0):
                     logging.info("BUY Call option of " + str(self.Call_Option_Quantity) + " quantity at price " + str(Call_b))
                     self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[0])], "BUY", self.Call_Option_Quantity, round(Call_b - (Call_b % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])]), 1))
                     
                 if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])] != 0 and abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) < self.P_L and Put_a !=0):
                     logging.info("SELL Put option of " + str(self.Put_Option_Quantity) + " quantity at price " + str(Put_a))
                     self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[1])], "SELL", self.Put_Option_Quantity, round(Put_a - (Put_a % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])]), 1))
                 
               
                
                 if (self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] >= 1 and self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] <= -1):  
                   
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) < self.S_L and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0): 
                         
                         logging.info("SELL Fut Stk of " + str(self.Underlying_Quantity) + " quantity at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])], "SELL", self.Underlying_Quantity, round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
     
                
                 
                
                 if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])] != 0 and abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) < self.C_L and Call_a != 0):
                     logging.info("SELL Call option of " + str(self.Call_Option_Quantity) + " quantity at price " + str(Call_a))
                     self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[0])], "SELL", self.Call_Option_Quantity, round(Call_a - (Call_a % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])]), 1))
                     
                 if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])] != 0 and abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) < self.P_L and Put_b !=0):
                     logging.info("BUY Put option of " + str(self.Put_Option_Quantity) + " quantity at price " + str(Put_b))
                     self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[1])], "BUY", self.Put_Option_Quantity, round(Put_b - (Put_b % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])]), 1))
                 
                    
                 if (self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] <= -1 and self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] >= 1): 
               
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) < self.S_L and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] !=0):   
                      
                         logging.info("BUY Fut Stk of " + str(self.Underlying_Quantity) + " quantity at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])], "BUY", self.Underlying_Quantity, round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
     
                 
                    
                 BDelta = (self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] * self.D_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) + (self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] * self.D_P[int(df_Current_Contract['Serial_Nu'].iloc[1])])
                 
                 if BDelta > 0:
                     
                     bdelta_stocks_qty = abs(BDelta * self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])])
                     
                     # execute limit order for stock
                   
                             
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] !=0):
                         logging.info("SELL Fut Stk of " + str(bdelta_stocks_qty) + " no of BDELTA QTY of (BDelta " + str(BDelta) +") at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])], "SELL", bdelta_stocks_qty, round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
                         
                 elif BDelta < 0:
                     
                     bdelta_stocks_qty = abs(BDelta * self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])])
                     
                     # execute limit order for stock
                    
                             
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] !=0):
                         logging.info("BUY Fut Stk of " + str(bdelta_stocks_qty) + " no of BDELTA QTY of (BDelta " + str(BDelta) +") at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])], "BUY", bdelta_stocks_qty, round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
  
    
    
    
    
    
  
            # When the position limit is exceeded   
             
            if (abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) >= self.C_L) or (abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) >= self.P_L) or (abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) >= self.S_L) :
                 
                
                 # if N_C < 0 that means lot of sell orders have been executed and now we have to start executing for buy order
                 if self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] < 0:
                     
                     Call_mid = (self.Call_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])] + self.Call_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])]) / 2
                     
                    
                     # (abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) >= self.C_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.       
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])] != 0 and (abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) >= self.C_L) and Call_mid !=0):
                         logging.info("BUY Call option of " + str(abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])])) + " no of lots at price " + str(Call_mid))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[0])],"BUY", abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]), round(Call_mid - (Call_mid % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])]), 1))
             
                 
                 # if N_C > 0 that means lot of buy orders have been executed and now we have to start executing for sell order   
                 if self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] > 0:
                     
                     Call_mid = (self.Call_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])] + self.Call_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[0])]) / 2
                     
                     # (abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) >= self.C_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.  
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])] != 0 and (abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]) >= self.C_L) and Call_mid !=0):
                         logging.info("SELL Call option of " + str(abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])])) + " no of lots at price " + str(Call_mid))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[0])],"SELL", abs(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])]), round(Call_mid - (Call_mid % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[0])]), 1))
             
                
                
                 # if N_P < 0 that means lot of sell orders have been executed and now we have to start executing for buy order
                 if self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] < 0:
                     
                     Put_mid = (self.Put_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])] + self.Put_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])]) / 2
              
                     # (abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) >= self.P_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.  
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])] != 0 and (abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) >= self.P_L) and Put_mid !=0):
                         logging.info("BUY Put option of " + str(abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])])) + " no of lots at price " + str(Put_mid))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[1])],"BUY", abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]), round(Put_mid - (Put_mid % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])]), 1))
                 
                    
                # if N_P > 0 that means lot of buy orders have been executed and now we have to start executing for sell order 
                 if self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] > 0:
                     
                     Put_mid = (self.Put_Bid_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])] + self.Put_Ask_Price[int(df_Current_Contract['Serial_Nu'].iloc[1])]) / 2
                     
                     # (abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) >= self.P_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.  
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])] != 0 and (abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]) >= self.P_L) and Put_mid !=0):
                         logging.info("SELL Put option of " + str(abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])])) + " no of lots at price " + str(Put_mid))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[1])],"SELL", abs(self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])]), round(Put_mid - (Put_mid % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[1])]), 1))
             
                     
          
                 # if N_S > 0 that means lot of buy orders have been executed and now we have to start executing for sell order
                 if self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])] > 0:
                           
                     # (abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) >= self.S_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.  
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and (abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) >= self.S_L) and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] !=0):
                         logging.info("SELL Fut Stk of " + str(abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])])) + " no of lots at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])],"SELL", abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]), round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
             
                
                 # if N_S < 0 that means lot of sell orders have been executed and now we have to start executing for buy order
                 if self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])] < 0:
                             
                     # (abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) >= self.S_L) this condition we are checking to ensure that the limit has been reached because in the outer "IF" condition we are checking the limits using "OR" operator thus we can't be sure which limit has been exceeded.  
                     if(self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0 and (abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]) >= self.S_L) and self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] !=0):
                         logging.info("BUY Fut Stk of " + str(abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])])) + " no of lots at price " + str(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])]))
                         self._send_lmt_order(self.contracts[int(df_Current_Contract['Serial_Nu'].iloc[2])],"BUY", abs(self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])]), round(self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] - (self.S[int(df_Current_Contract['Serial_Nu'].iloc[2])] % self.minimumTick[int(df_Current_Contract['Serial_Nu'].iloc[2])]), 1))
            
             
            
            if(self.N_C[int(df_Current_Contract['Serial_Nu'].iloc[0])] != 0  or self.N_P[int(df_Current_Contract['Serial_Nu'].iloc[1])] != 0 or self.N_S[int(df_Current_Contract['Serial_Nu'].iloc[2])] != 0):
                self.order_for_placing = False  #Once order placed make it false until  pnlSingle function get the new data for position.
         
     #*****************************Tick Price(BID/ASK/LTP)  end*****************************#  
                 
    
    #****************************PandL (UPL/RPL) start*****************************#      
        
    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float, unrealizedPnL: float, realizedPnL: float, value: float):
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
        
        c = self.contracts[reqId]
      
        
        if c.right == 'C':
            self.N_C[reqId] = pos
            self.UPL[reqId] = unrealizedPnL
            self.RPL[reqId] = realizedPnL
            
        elif c.right == 'P':
            self.N_P[reqId] = pos
            self.UPL[reqId] = unrealizedPnL
            self.RPL[reqId] = realizedPnL
        else:
            self.N_S[reqId] = pos
            self.UPL[reqId] = unrealizedPnL
            self.RPL[reqId] = realizedPnL
            
        self.open_order_status_end = True
        self.order_for_placing = True
        
        
    #****************************PandL (UPL/RPL) end*******************************# 


    
    #*************************************Order routing start******************************#
       
    def _send_lmt_order(self, contract, action, qty, lmtPrice):
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = qty
        order.lmtPrice = lmtPrice
       
        order_id = self.newOrderId()

 
        self.placeOrder(order_id, contract, order)
    def nextValidId(self, orderId:int):
        self._order_id = orderId
       
    def newOrderId(self):
        oid = self._order_id
        self._order_id+=1
        return oid       
   
    #*************************************Order routing  end*******************************# 
    
    
SetupLogger()
logging.debug("now is %s", datetime.now())
logging.getLogger().setLevel(logging.INFO)


app = TestApp()
app.connect('127.0.0.1', 7497, 1)

contracts = []

# Read the csv file for Contract Symbols
stocklist = pd.read_csv("C:\\JP_Project_NFLX\\Mapping_MICHELIN_jp.csv")


for i in range(len(stocklist)):
    
    if stocklist['Type'].iloc[i] == 'OPT':
        print(stocklist['IBSymbol'].iloc[i])
        c = Contract()                
        c.symbol = stocklist['IBSymbol'].iloc[i]
        c.secType = stocklist['Type'].iloc[i]
        c.lastTradeDateOrContractMonth=stocklist['Expiry'].iloc[i]
        c.strike = stocklist['Strike'].iloc[i]
        c.right = stocklist['right'].iloc[i]
        c.exchange = stocklist['exchange'].iloc[i]
        c.currency = stocklist['currency'].iloc[i]
        c.multiplier = stocklist['multiplier'].iloc[i]
        contracts.append(c)
    
    else :
        # For underlying stock
        print(stocklist['IBSymbol'].iloc[i])
        c = Contract()
        c.symbol = stocklist['IBSymbol'].iloc[i]
        c.secType = stocklist['Type'].iloc[i]
        c.exchange = stocklist['exchange'].iloc[i]
        c.currency = stocklist['currency'].iloc[i]
        
        if(stocklist['Type'].iloc[i] == 'FUT'):
            c.lastTradeDateOrContractMonth = stocklist['Expiry'].iloc[i]
            c.multiplier = stocklist['multiplier'].iloc[i]
            
        contracts.append(c)
    



app.contracts = contracts

for i in range(len(contracts)):
    
    if contracts[i].secType == 'OPT':
        
        # def tickPrice(self, reqId: TickerId , tickType, price: float, attrib): call_bid, put_bid, call_ask, put_ask (Call Back Function)
        app.reqMktData(i, contracts[i], "101", False, False, [])
        
        # def tickOptionComputation(delta, gamma, vega, theta) (Call Back Function)
        app.reqMktData(i, contracts[i], "", False, False, [])
        
    else: # For underlying stock
        
        #def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float): (Call Back Function)
        app.reqTickByTickData(i, contracts[i], "MidPoint", 0, False)
        #def tickReqParams(self, reqId: int, minTick:float, bboExchange:str, snapshotPermissions:int):
        app.reqMktData(i, contracts[i], '', False, False, [])


                     
app.run()
            
