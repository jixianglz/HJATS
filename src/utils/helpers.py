"""
工具函数
"""
from src.utils.constants import FREQ_TO_SECONDS


def trans_frq2sec(frequency: str) -> int:
    """
    将频率字符串转换为秒数

    Args:
        frequency: 如 "1MIN", "5MINS", "15MINS", "1HOUR", "1DAY"

    Returns:
        对应的秒数

    Raises:
        ValueError: 不支持的频率
    """
    seconds = FREQ_TO_SECONDS.get(frequency)
    if seconds is None:
        raise ValueError(f"Unsupported frequency: {frequency}, "
                         f"supported: {list(FREQ_TO_SECONDS.keys())}")
    return seconds


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
        'white': '\033[37m',
    }

    bg_colors = {
        'red': '\033[41m',
        'green': '\033[42m',
        'yellow': '\033[43m',
        'blue': '\033[44m',
        'magenta': '\033[45m',
        'cyan': '\033[46m',
        'white': '\033[47m',
    }

    style = ''
    if bold:
        style += '\033[1m'
    if underline:
        style += '\033[4m'

    color_code = colors.get(color.lower(), '\033[37m')
    bg_code = bg_colors.get(bg_color.lower(), '') if bg_color else ''

    print(f"{style}{bg_code}{color_code}{text}\033[0m")