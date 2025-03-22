import sys
import time

import numpy as np
from matplotlib.pyplot import MultipleLocator
from matplotlib.backends.qt_compat import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from multiprocessing import Process


class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)


        self.dynamic_canvas = FigureCanvas(Figure(figsize=(10, 8)))
        
        layout.addWidget(self.dynamic_canvas)
        self.addToolBar(QtCore.Qt.BottomToolBarArea,
                        NavigationToolbar(self.dynamic_canvas, self))



        self.dynamic_ax = self.dynamic_canvas.figure.subplots()
        #self._line, = self.dynamic_ax.plot([],[])
        

    def update_canvas(self,rawdata_show):
        
        x=rawdata_show.index.to_numpy()
        y=rawdata_show['close'].values
        length=len(rawdata_show)

        # Use fixed vertical limits to prevent autoscaling changing the scale
        # of the axis.
        #self._dynamic_ax.set_ylim(-1.1, 1.1)
        # Shift the sinusoid as a function of time.
        if(length<20):
            x_major_locator=MultipleLocator(1)
        else:
            x_major_locator=MultipleLocator(int(length/20))
        #y_major_locator=MultipleLocator(1)

        #self._line.set_data(x,y)
        self.dynamic_ax.plot(x,y)
        self.dynamic_ax.figure.canvas.draw()
        self.dynamic_ax.xaxis.set_major_locator(x_major_locator)


if __name__ == "__main__":
    # Check whether there is already a running QApplication (e.g., if running
    # from an IDE).
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ApplicationWindow()
    app.show()
    app.activateWindow()
   # app.raise_()
   # qapp.exec_()