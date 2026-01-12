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
        
def print_colored(text, color='white', bg_color=None, bold=False, underline=False):
    """
    打印彩色文字
    
    Args:
        text: 要打印的文字
        color: 文字颜色 ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
        bg_color: 背景颜色 (同上)
        bold: 是否粗体
        underline: 是否下划线
    """
    
    colors = {
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[29m'
    }
    
    bg_colors = {
        'red': '\033[41m',
        'green': '\033[42m',
        'yellow': '\033[43m',
        'blue': '\033[44m',
        'magenta': '\033[45m',
        'cyan': '\033[46m',
        'white': '\033[47m'
    }
    
    style = ''
    if bold:
        style += '\033[1m'
    if underline:
        style += '\033[4m'
    
    color_code = colors.get(color.lower(), '\033[37m')
    bg_code = bg_colors.get(bg_color.lower(), '') if bg_color else ''
    
    print(f"{style}{bg_code}{color_code}{text}\033[0m")
