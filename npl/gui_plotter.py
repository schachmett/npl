"""Provides a widget that plots the spectra and helping lines, also
provides means for altering its appearance."""
# pylint: disable=wrong-import-position

import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from matplotlib.backends.backend_gtk3 import (
    NavigationToolbar2GTK3 as NavigationToolbar)
from matplotlib.backends.backend_gtk3agg import (
    FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.figure import Figure
import numpy as np

from npl import __config__
from npl.fileio import RSFHandler
from npl.plotter_elements import SpanSelector, DraggableVLine, PeakSelector
from npl.gui_dialogs import SelectElementsDialog


class CanvasBox(Gtk.Box):
    """Plotting area box."""
    def __init__(self, app, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.parent = parent
        self.figure = SpectrumFigure()
        self.navbar = MPLNavBar(self.figure, self.parent)

        self.rsf = {"elements": [], "source": ""}

        self.pack_start(self.figure.canvas, True, True, 0)
        self.pack_start(self.navbar, False, False, 0)

        self.refresh()

    def refresh(self, keepaxes=False):
        """Draws on canvas."""
        self.figure.store_axlims()
        self.figure.ax.cla()
        self.figure.plot(self.app.s_container)
        if keepaxes:
            self.figure.adjust_axlims()
        else:
            self.figure.recenter_view()
        self.figure.set_ticks()
        self.figure.plot_rsf(self.rsf["elements"], self.rsf["source"])
        self.figure.canvas.draw_idle()

    def show_rsf(self, *_ignore):
        """ makes a SelectElementsDialog and hands the user input to the
        plotter """
        dialog = SelectElementsDialog(self.parent,
                                      self.rsf["elements"],
                                      self.rsf["source"])
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            elements, source = dialog.get_user_input()
            self.rsf["elements"] = elements
            self.rsf["source"] = source
            self.refresh(keepaxes=True)
        dialog.destroy()

    def get_span(self, callback, **kwargs):
        """Just gets a span from the user."""
        self.figure.get_span(callback, **kwargs)

    def draw_peak(self, callback):
        """Lets the user draw a peak and calls callback(amplitude, fwhm)."""
        self.figure.draw_peak(callback)


class BeautifulFigure(Figure):
    """A customized canvas."""
    def __init__(self):
        # pylint: disable=invalid-name
        super().__init__(figsize=(10, 10), dpi=80)
        self.canvas = FigureCanvas(self)
        self.ax = self.add_axes([-0.005, 0.0, 1.01, 1.005])

        self.now_xy = [0, 0, 1, 1]
        self.s_xy = [np.inf, -np.inf, np.inf, -np.inf]

    def lock(self, obj):
        """Lock the canvas."""
        self.canvas.widgetlock(obj)

    def unlock(self, obj):
        """Unlock the canvas."""
        self.canvas.widgetlock.release(obj)

    def set_ticks(self):
        """Configures axes ticks."""
        self.ax.tick_params(
            reset=True,
            axis="both",
            direction="in",
            pad=-20,
            labelsize="large",
            labelcolor="blue",
            color="blue",
            labelleft=False,
            top=False,
            left=False,
            right=False)
        if self.s_xy[0] == np.inf:
            self.ax.tick_params(
                which="both",
                bottom=False,
                top=False,
                left=False,
                right=False,
                labelbottom=False)

    def store_axlims(self):
        """Stores axis limits in self.now_xy."""
        self.now_xy[1], self.now_xy[0] = self.ax.get_xlim()
        self.now_xy[2], self.now_xy[3] = self.ax.get_ylim()

    def adjust_axlims(self):
        """Sets the axis limits."""
        if np.all(np.isfinite(self.now_xy)):
            self.ax.set_xlim(*self.now_xy[1::-1])
            self.ax.set_ylim(*self.now_xy[2:])

    def recenter_view(self):
        """Focuses view on current plot."""
        if self.now_xy != self.s_xy:
            self.now_xy = self.s_xy
        self.adjust_axlims()


class SpectrumFigure(BeautifulFigure):
    """Axes object containing the methods for plotting Spectra."""
    def __init__(self):
        super().__init__()
        rsf_file = os.path.join(__config__.get("general", "basedir"), "rsf.db")
        self.rsfhandler = RSFHandler(rsf_file)
        self.span_selector = SpanSelector(
            self.ax, lambda *args: None, "horizontal", span_stays=True,
            useblit=True)
        self.span_selector.active = False
        self.peak_selector = PeakSelector(
            self.ax, lambda *args: None, peak_stays=False, useblit=True)
        self.peak_selector.active = False
        self.dlines = []

    def plot_spectrum(self, spectrum):
        """Spectrum plotting."""
        lineprops = {
            "color": "black",
            "linewidth": 1,
            "linestyle": "-",
            "alpha": 1}
        self.ax.plot(
            spectrum.energy, spectrum.intensity,
            label=spectrum.name, **lineprops)
        self.s_xy = [
            min(self.s_xy[0], min(spectrum.energy)),
            max(self.s_xy[1], max(spectrum.energy)),
            min(self.s_xy[2], min(spectrum.intensity)),
            max(self.s_xy[3], max(spectrum.intensity * 1.05))]

    def plot_region(self, region):
        """Region plotting."""
        lineprops = {
            "color": "blue",
            "linewidth": 2,
            "linestyle": "-",
            "alpha": 0.5}
        line = self.ax.axvline(region.emin, 0, 1, **lineprops)
        self.dlines.append(DraggableRegionBound(line, region, "emin"))
        line = self.ax.axvline(region.emax, 0, 1, **lineprops)
        self.dlines.append(DraggableRegionBound(line, region, "emax"))
        # region.calculate_background()
        if ("b" in region.spectrum.visibility
                and region.background is not None):
            lineprops = {
                "color": "red",
                "linewidth": 1,
                "linestyle": "--",
                "alpha": 1}
            self.ax.plot(
                region.energy, region.background, **lineprops)

    def plot_peaks(self, region):
        """Peak and model plotting."""
        lineprops = {
            "color": "blue",
            "linewidth": 1,
            "linestyle": "--"}
        if region.fit_intensity is not None:
            self.ax.plot(
                region.energy,
                region.fit_intensity + region.background,
                **lineprops)
        lineprops = {
            "color": "green",
            "linewidth": 1,
            "linestyle": "--"}
        for peak in region.peaks:
            if peak.fit_intensity is not None:
                self.ax.plot(
                    region.energy,
                    peak.fit_intensity + region.background,
                    **lineprops)

    def plot(self, container):
        """Plots a spectrum."""
        self.dlines = []
        if container:
            self.s_xy = [np.inf, -np.inf, np.inf, -np.inf]
        for spectrum in container:
            if "d" in spectrum.visibility:
                self.plot_spectrum(spectrum)
            else:
                continue
            if "r" in spectrum.visibility:
                for region in spectrum.regions:
                    self.plot_region(region)
            if "p" in spectrum.visibility:
                for region in spectrum.regions:
                    self.plot_peaks(region)

    def plot_rsf(self, elements, source):
        """Plots RSF values for a certain element with given X-ray souce."""
        if not elements:
            return
        peakdata = []
        for element in elements:
            peaks = self.rsfhandler.get_element(element, source)
            peakdata.append(peaks)

        max_rsf = max(max(
            [[(x["RSF"] + 1e-9) for x in dicts] for dicts in peakdata]))
        normfactor = (self.now_xy[3] / max_rsf * 0.8)
        colorcycle = "gcmybr"*10
        for i, peaks in enumerate(peakdata):
            for peak in peaks:
                if peak["RSF"] == 0:
                    rsf = 0.5 * self.now_xy[3]
                else:
                    rsf = peak["RSF"] * normfactor
                self.ax.vlines(peak["BE"], 0, rsf, colors=colorcycle[i], lw=2)
                self.ax.annotate(
                    peak["Fullname"],
                    xy=[peak["BE"], rsf + self.now_xy[3] * 0.015],
                    color="black",
                    textcoords="data")

    def get_span(self, callback, **kwargs):
        """Makes a SpanSelector and uses it."""
        def on_selected(emin, emax):
            """Callback for the SpanSelector."""
            self.span_selector.active = False
            callback(emin, emax)
        self.disable_actions()
        rectprops = {}
        rectprops["alpha"] = kwargs.get("alpha", 0.5)
        rectprops["fill"] = kwargs.get("fill", False)
        rectprops["edgecolor"] = kwargs.get("edgecolor", "black")
        rectprops["linewidth"] = kwargs.get("linewidth", 1)
        rectprops["linestyle"] = kwargs.get("linestyle", "-")
        self.span_selector.set_rectprops(rectprops)
        self.span_selector.onselect = on_selected
        self.span_selector.active = True

    def draw_peak(self, callback, **kwargs):
        """Draws a rudimentary peak (a triangle -> sets maximum and fwhm)."""
        def on_selected(center, amp, angle):
            """Callback for the PeakSelector"""
            self.peak_selector.active = False
            callback(center, amp, angle)
        self.disable_actions()
        wedgeprops = {}
        wedgeprops["alpha"] = kwargs.get("alpha", 0.5)
        wedgeprops["fill"] = kwargs.get("fill", True)
        wedgeprops["edgecolor"] = kwargs.get("edgecolor", "black")
        wedgeprops["facecolor"] = kwargs.get("facecolor", "red")
        wedgeprops["linewidth"] = kwargs.get("linewidth", 1)
        self.peak_selector.set_wedgeprops(wedgeprops)
        self.peak_selector.onselect = on_selected
        self.peak_selector.active = True

    def disable_actions(self):
        """Disables all tools."""
        self.span_selector.active = False
        self.peak_selector.active = False


class MPLNavBar(NavigationToolbar):
    """Navbar for the canvas."""
    def __init__(self, figure, parent):
        self.figure = figure
        self.parent = parent
        self.toolitems = (
            ('Fullscreen', 'Fit view to data', 'home', 'fit_view'),
            ('Back', 'Back to  previous view', 'back', 'back'),
            ('Forward', 'Forward to next view', 'forward', 'forward'),
            (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', 'move',
             'pan'),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
            (None, None, None, None),
            ('Save', 'Save the figure', 'filesave', 'save_figure'))
        super().__init__(self.figure.canvas, self.parent)

    def fit_view(self, _event):
        """Centers the view to plotted graphs, mapped to home button."""
        if self._views.empty():
            self.push_current()
        self.figure.recenter_view()
        self.parent.refresh(rview=False)
        self.push_current()
        self._update_view()

    def disable(self):
        """Disables the NavBars current tool (pan/zoom)."""
        self._active = None
        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''
        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''
        self.canvas.widgetlock.release(self)
        for axs in self.canvas.figure.get_axes():
            axs.set_navigate_mode(self._active)


class DraggableRegionBound(DraggableVLine):
    """Takes a line marking a region boundary and makes it draggable."""
    def __init__(self, line, region, attr):
        super().__init__(line)
        self.region = region
        self.attr = attr

    def on_release(self, event):
        """When the mouse button is released."""
        if self.lock is not self:
            return

        if self.attr == "emin":
            self.region.set(emin=self.line.get_xdata()[0])
        if self.attr == "emax":
            self.region.set(emax=self.line.get_xdata()[0])

        super().on_release(event)
