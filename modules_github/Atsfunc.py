# -*- coding: utf-8 -*-
"""
Created on Thu Jan  6 07:04:42 2022

@author: Administrator
"""

from Constants import *

def transFrq2Sec(consfreq):
    
    if consfreq==FREQ_1MIN:
        return 60
    if consfreq==FREQ_5MINS:
        return 300
    if consfreq==FREQ_15MINS:
        return 900
    if consfreq==FREQ_30MINS:
        return 1800
    if consfreq==FREQ_1HOUR:
        return 3600
    if consfreq==FREQ_1HOURS:
        return 14400
    if consfreq==FREQ_1DAY:
        return 86400