""" manages the canvas """

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo
import matplotlib.pyplot as plt
import numpy as np


class Plotter():
    """ plots shit """
    k_alpha = {"Al": 1486.3,
               "Mg": 1253.4}

    def __init__(self):
        self.fig = plt.figure(figsize=(10, 10), dpi=80)
        self.axes = self.fig.add_axes([0, 0, 1, 1])
        self.canvas = FigureCanvasGTK3Cairo(self.fig)
        self.spec_xy = [np.inf, -np.inf, np.inf, -np.inf]
        self.act_xy = [0, 0, 1, 1]
        self.container = []
        
        self.rsfdicts = []
        self.source = None

        self.xrange1 = None
        self.xrange2 = None

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
        self.plot_xrange()
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

    def plot_rsf(self, source=None, dicts=None):
        """ draws rsf intensities for selected elements, dicts like:
        {IsAuger: bool, BE: float, Fullname: string, RSF: float} """
        if source is not None:
            self.source = source
        if dicts is not None:
            self.rsfdicts = dicts
        if len(self.rsfdicts) == 0 or self.source is None:
            return
                
        normfactor = self.act_xy[3] / max([(x["RSF"] + 1e-9) for x in self.rsfdicts]) * 0.8
        for peak in self.rsfdicts:
            if peak["IsAuger"]:
                rsf = self.act_xy[3] * 0.5
                energy = self.k_alpha[self.source] - peak["BE"]
            else:
                rsf = peak["RSF"] * normfactor
                energy = peak["BE"]
            self.axes.plot([energy, energy],
                           [0, rsf],
                           c=peak["color"],
                           lw=2)
            self.axes.annotate(peak["Fullname"],
                               xy=[energy, rsf + self.act_xy[3] * 0.015],
                               color="blue",
                               textcoords="data")

    def get_xrange(self):
        """ creates XRangeSelector and gets an energy region """
        self.sel = XRangeSelector(self)
        self.sel.connect("changed", self.change_xrange)

    def change_xrange(self, selector, x1, x2):
        self.xrange1 = x1
        self.xrange2 = x2
        self.plot()
        
    def plot_xrange(self):
        if self.xrange1 is None and self.xrange2 is None:
            return
        self.axes.plot([self.xrange1, self.xrange1],
                       [self.act_xy[2], self.act_xy[3]],
                       c="k",
                       ls="--",
                       lw=2)
        if self.xrange2 is not None:
            self.axes.plot([self.xrange2, self.xrange2],
                           [self.act_xy[2], self.act_xy[3]],
                           c="k",
                           ls="--",
                           lw=2)

    def change_rsf(self, source, dicts):
        self.source = source
        self.rsfdicts = dicts
        self.plot()

    def recenter_view(self):
        """ focuses view on current plot """
        if self.act_xy != self.spec_xy:
            self.act_xy = self.spec_xy
            self.axrange()


class XRangeSelector(GObject.GObject):
    """ lets the user select an X range either by clicking left and right
    or by dragging from left to right """
    __gsignals__ = {"changed": (GObject.SIGNAL_RUN_FIRST, None,
                                (GObject.TYPE_PYOBJECT,
                                 GObject.TYPE_PYOBJECT,))}

    def __init__(self, plotter):
        __gsignals__ = {"changed": (GObject.SIGNAL_RUN_FIRST, None,
                                    (float, float,))}
        super().__init__()
        self.plotter = plotter
        self.canvas = self.plotter.get_canvas()
        self.press_handle = self.canvas.mpl_connect("button_press_event", self.on_press)
        self.release_handle = self.canvas.mpl_connect("button_release_event", self.on_release)

        self.x1 = None
        self.x2 = None

    def on_press(self, event):
        delta_x = self.plotter.act_xy[2] - self.plotter.act_xy[0]
        if event.button == 1 and self.x1 is None:
            self.x1 = event.xdata
            self.emit("changed", self.x1, self.x2)

    def on_release(self, event):
        if event.button == 1:
            if self.x1 is None:
                return
            delta_x = self.plotter.act_xy[2] - self.plotter.act_xy[0]
            if abs(event.xdata - self.x1) <= delta_x / 100:
                self.x1  = event.xdata
                self.emit("changed", self.x1, self.x2)
            elif self.x2 is None or abs(event.xdata - self.x2) <= delta_x / 100:
                self.x2 = event.xdata
                self.emit("changed", self.x1, self.x2)

    def disconnect(self):
        self.canvas.mpl_disconnect(self.press_handle)
        self.canvas.mpl_disconnect(self.release_handle)
