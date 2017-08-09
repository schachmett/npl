"""manages the canvas"""
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo
import matplotlib.pyplot as plt
import numpy as np


class Plotter():
    """plots shit"""
    def __init__(self):
        self.fig = plt.figure(figsize=(10, 10), dpi=80)
        self.axes = self.fig.add_axes([0, 0, 1, 1])
        self.canvas = FigureCanvasGTK3Cairo(self.fig)
        self.spec_xy = [np.inf, -np.inf, np.inf, -np.inf]
        self.act_xy = [0, 0, 1, 1]

        self.axes.tick_params(axis='both', which='major', pad=-20)
        self.axes.invert_xaxis()
#         self.make_pretty()

    def get_canvas(self):
        """gives canvas object"""
        return self.canvas

    def axrange(self):
        """set axes"""
        if np.all(np.isfinite(self.act_xy)):
            self.axes.axis(self.act_xy)
        self.axes.invert_xaxis()

    def plot(self, container, keepaxes=False):
        """plots the stuff from the container"""
        self.spec_xy = [np.inf, -np.inf, np.inf, -np.inf]
        self.act_xy = self.axes.axis()
        self.axes.cla()
        for spectrum in container:
            if spectrum["Visibility"] == "default":
                self.axes.plot(spectrum["Energy"], spectrum["Intensity"],
                               label=spectrum["Notes"], c="k", lw=1)
                self.spec_xy = [min(self.spec_xy[0],
                                    min(spectrum["Energy"])),
                                max(self.spec_xy[1],
                                    max(spectrum["Energy"])),
                                min(self.spec_xy[2],
                                    min(spectrum["Intensity"])),
                                max(self.spec_xy[3],
                                    max(spectrum["Intensity"])) * 1.05]
        if not keepaxes:
            self.recenter_view()
        else:
            self.axrange()
        self.canvas.draw_idle()

#     def make_pretty(self):
#         """manages ticks and stuff"""
#         plt.yticks(rotation='vertical')
#         self.ax.xaxis.get_major_ticks()[0].set_visible(False)
#         self.ax.xaxis.get_major_ticks()[-1].set_visible(False)
#         self.ax.yaxis.get_major_ticks()[0].set_visible(False)
#         self.ax.yaxis.get_major_ticks()[-1].set_visible(False)

    def draw_rsf(self):
        """draws rsf intensities for arbitrary elements"""
        pass

    def recenter_view(self):
        """focuses view on current plot"""
        if self.act_xy != self.spec_xy:
            self.act_xy = self.spec_xy
            self.axrange()
