"""Provides a widget that plots the spectra and helping lines, also
provides means for altering its appearance."""
# pylint: disable=wrong-import-position

import os
import re

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
from npl.containers import Region
from npl.custom_spanselector import SpanSelector


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

    def create_region(self, spectra):
        """Calls the plotter energy range selector method."""
        if len(spectra) == 1:
            self.figure.create_region(spectra[0])
        else:
            self.parent.message("More than one spectrum selected")

    def get_span(self, callback):
        """Just gets a span from the user."""
        self.figure.get_span(callback)


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
        self.span_selector = None
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
        region.calculate_background()
        if ("b" in region.spectrum.visibility
                and region.background is not None):
            lineprops = {
                "color": "red",
                "linewidth": 1,
                "linestyle": "--",
                "alpha": 1}
            self.ax.plot(
                region.energy, region.background, **lineprops)

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

    def create_region(self, spectrum):
        """Makes a SpanSelector and creates a region from it."""
        def on_region_selected(emin, emax):
            """Creates a new region in Spectrum object."""
            region = Region(spectrum=spectrum, emin=emin, emax=emax)
            spectrum.regions.append(region)
            region.emin = region.emin       #TODO fix this workaround
            self.span_selector.active = False
        self.span_selector = SpanSelector(
            self.ax,
            on_region_selected,
            "horizontal",
            span_stays=True,
            useblit=True,
            rectprops={
                "alpha": 0.5,
                "fill": False,
                "edgecolor": "blue",
                "linewidth": 2,
                "linestyle": "-"})

    def get_span(self, callback):
        """Makes a SpanSelector and uses it."""
        def on_selected(emin, emax):
            """Creates a new region in Spectrum object."""
            self.span_selector.active = False
            callback(emin, emax)
        self.span_selector = SpanSelector(
            self.ax,
            on_selected,
            "horizontal",
            span_stays=True,
            useblit=True,
            rectprops={
                "alpha": 0.5,
                "fill": False,
                "edgecolor": "black",
                "linewidth": 1,
                "linestyle": "-"})


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


class SelectElementsDialog(Gtk.Dialog):
    """Lets the user select elements and a source for rsf plotting."""
    sources = ["Al", "Mg"]
    def __init__(self, parent, default_elements=None, default_source=None):
        super().__init__(
            "Element Library", parent, 0,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK))
        okbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.OK)
        okbutton.set_can_default(True)
        okbutton.grab_default()

        self.box = self.get_content_area()
        self.source_combo = Gtk.ComboBoxText()
        self.source_combo.set_entry_text_column(0)
        for colname in self.sources:
            self.source_combo.append_text(colname)
        if default_source in self.sources:
            idx = self.sources.index(default_source)
            self.source_combo.set_active(idx)
        elif default_source != "":
            self.source_combo.append_text(default_source)
            self.source_combo.set_active(-1)
        else:
            self.source_combo.set_active(0)
        self.elements_entry = Gtk.Entry()
        self.elements_entry.set_text(" ".join(default_elements))

        rowbox1 = Gtk.Box()
        rowbox1.pack_start(
            Gtk.Label("Source", width_chars=15, xalign=0), False, False, 10)
        rowbox1.pack_start(self.source_combo, True, True, 10)
        rowbox2 = Gtk.Box()
        rowbox2.pack_start(
            Gtk.Label("Elements", width_chars=15, xalign=0), False, False, 10)
        rowbox2.pack_start(self.elements_entry, True, True, 10)
        self.box.pack_start(rowbox1, False, False, 2)
        self.box.pack_start(rowbox2, False, False, 2)
        self.show_all()

    def get_user_input(self):
        """Gives elements and Sources selected."""
        source = self.source_combo.get_active_text()
        elementstring = self.elements_entry.get_text()
        elements = re.findall(r"[\w]+", elementstring)
        elements = [element.title() for element in elements]
        return [elements, source]


class DraggableVLine():
    """A draggable vertical line in the plot."""
    lock = None
    def __init__(self, line):
        self.line = line
        self.press = None
        self.background = None

        self.connect()

    def change_line(self, line):
        """Gets another line to drag."""
        self.disconnect()
        self.line = line
        self.connect()

    def connect(self):
        """Connect to the signals."""
        self.cidpress = self.line.figure.canvas.mpl_connect(
            "button_press_event", self.on_press)
        self.cidrelease = self.line.figure.canvas.mpl_connect(
            "button_release_event", self.on_release)
        self.cidmotion = self.line.figure.canvas.mpl_connect(
            "motion_notify_event", self.on_motion)

    def disconnect(self):
        """Disconnects from canvas signals."""
        self.line.figure.canvas.mpl_disconnect(self.cidpress)
        self.line.figure.canvas.mpl_disconnect(self.cidrelease)
        self.line.figure.canvas.mpl_disconnect(self.cidmotion)

    def on_press(self, event):
        """When the mouse button is pressed."""
        if event.inaxes != self.line.axes:
            return
        if self.lock is not None:
            return
        if not self.line.contains(event)[0]:
            return

        self.press = self.line.get_xdata(), event.xdata, event.ydata
        self.lock = self

        self.line.set_animated(True)
        self.line.figure.canvas.draw()
        self.background = self.line.figure.canvas.copy_from_bbox(
            self.line.axes.bbox)
        self.line.axes.draw_artist(self.line)
        self.line.figure.canvas.blit(self.line.axes.bbox)

    def on_release(self, _event):
        """When the mouse button is released."""
        if self.lock is not self:
            return

        self.press = None
        self.lock = None

        self.line.set_animated(False)
        self.background = None
        self.line.figure.canvas.draw()

    def on_motion(self, event):
        """When the mouse is moved in pressed state."""
        if self.lock is not self:
            return
        if event.inaxes != self.line.axes:
            return

        xdata, xpress, _ = self.press
        self.line.set_xdata(xdata)
        xdiff = event.xdata - xpress
        self.line.set_xdata([self.line.get_xdata()[0] + xdiff] * 2)

        self.line.figure.canvas.restore_region(self.background)
        self.line.axes.draw_artist(self.line)
        self.line.figure.canvas.blit(self.line.axes.bbox)


class DraggableRegionBound(DraggableVLine):
    """Takes a line marking a region boundary and makes it draggable."""
    def __init__(self, line, region, attr):
        super().__init__(line)
        self.region = region
        self.attr = attr

    def on_release(self, _event):
        """When the mouse button is released."""
        if self.lock is not self:
            return

        setattr(self.region, self.attr, self.line.get_xdata()[0])

        self.press = None
        self.lock = None

        self.line.set_animated(False)
        self.background = None
        self.line.figure.canvas.draw()
