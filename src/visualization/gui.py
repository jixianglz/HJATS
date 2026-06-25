"""
可视化客户端 - 使用 matplotlib 实时显示回测K线和指标
"""
import logging
import numpy as np
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas, NavigationToolbar2QT
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class VisualizationWindow(QtWidgets.QMainWindow):
    """回测可视化窗口"""

    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        self.dynamic_canvas = FigureCanvas(Figure(figsize=(10, 8)))
        layout.addWidget(self.dynamic_canvas)
        self.addToolBar(
            QtCore.Qt.BottomToolBarArea,
            NavigationToolbar2QT(self.dynamic_canvas, self),
        )

        self.dynamic_ax = self.dynamic_canvas.figure.subplots()

    def update_canvas(self, rawdata_show):
        """更新K线图"""
        x = rawdata_show.index.to_numpy()
        y = rawdata_show['close'].values
        length = len(rawdata_show)

        self.dynamic_ax.clear()
        self.dynamic_ax.plot(x, y)
        self.dynamic_ax.figure.canvas.draw()


class VisualizationClient:
    """
    可视化客户端封装

    简化 GUI 的创建和更新流程
    """

    def __init__(self):
        self.app = None
        self.window = None
        self._initialized = False

    def init(self):
        """初始化 GUI 应用"""
        if self._initialized:
            return

        qapp = QtWidgets.QApplication.instance()
        if not qapp:
            self.app = QtWidgets.QApplication([])
        self.window = VisualizationWindow()
        self.window.show()
        self._initialized = True

    def update(self, rawdata_show, signal=None, indicators=None,
               indicators_w2=None, floating_asset_line=None,
               asset_line=None, instant_draw=False):
        """更新图表"""
        if not self._initialized:
            self.init()

        self.window.update_canvas(rawdata_show)

        if instant_draw:
            self.window.dynamic_canvas.figure.canvas.draw()

    def draw_results(self):
        """绘制最终结果"""
        logger.info("[GUI] Drawing final results")
        # 最终绘制逻辑可以在后续版本中增强

    def close(self):
        """关闭 GUI"""
        if self.window:
            self.window.close()