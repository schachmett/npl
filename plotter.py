""" manages the canvas """
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo
import matplotlib.pyplot as plt
import numpy as np


class Plotter():
    """ plots shit """
    def __init__(self):
        self.fig = plt.figure(figsize=(10, 10), dpi=80)
        self.axes = self.fig.add_axes([0, 0, 1, 1])
        self.canvas = FigureCanvasGTK3Cairo(self.fig)
        self.spec_xy = [np.inf, -np.inf, np.inf, -np.inf]
        self.act_xy = [0, 0, 1, 1]
        self.container = []
        self.rsfdicts = []

        self.axes.tick_params(axis='both', which='major', pad=-20)
        self.axes.invert_xaxis()

    def get_canvas(self):
        """ gives canvas object """
        return self.canvas

    def axrange(self):
        """ set axes """
        if np.all(np.isfinite(self.act_xy)):
            self.axes.axis(self.act_xy)
        self.axes.invert_xaxis()

    def plot(self, container=None, keepaxes=False):
        """ plots the stuff from the container """
        if container is not None:
            self.container = container
        self.spec_xy = [np.inf, -np.inf, np.inf, -np.inf]
        self.act_xy = self.axes.axis()
        self.axes.cla()
        for spectrum in self.container:
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
        self.plot_rsf()
        self.beautify()

    def beautify(self):
        """ makes axes ticks great again and such """
        if len(self.container) == 0:
            plt.tick_params(reset=True,
                            axis="both",
                            which="both",
                            bottom=False,
                            top=False,
                            left=False,
                            right=False,
                            labelbottom=False,
                            labelleft=False)
        else:
            plt.tick_params(reset=True,
                            axis="both",
                            direction="in",
                            pad=-20,
                            labelsize="large",
                            labelleft=False)

    def plot_rsf(self, dicts=None):
        """ draws rsf intensities for selected elements, dicts like:
        {IsAuger: bool, BE: float, Fullname: string, RSF: float} """
        if dicts is not None:
            self.rsfdicts = dicts
        if len(self.rsfdicts) == 0:
            return
        normfactor = self.act_xy[3] / max([x["RSF"] for x in self.rsfdicts]) * 0.8
        for peak in self.rsfdicts:
            self.axes.plot([peak["BE"], peak["BE"]],
                           [0, peak["RSF"] * normfactor],
                           c=peak["color"], lw=1)
            self.axes.annotate(peak["Fullname"],
                               xy=[peak["BE"], peak["RSF"] * normfactor],
                               textcoords="data")

    def change_rsf(self, dicts):
        self.rsfdicts = dicts
        self.plot()

    def recenter_view(self):
        """ focuses view on current plot """
        if self.act_xy != self.spec_xy:
            self.act_xy = self.spec_xy
            self.axrange()

if __name__ == "__main__":
    pass
