"""Provides a widget that plots the spectra and helping lines, also
provides means for altering its appearance."""
# pylint: disable=wrong-import-position

import os
import re

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from matplotlib.backends.backend_gtk3 import (NavigationToolbar2GTK3
                                              as NavigationToolbar)
from matplotlib.backends.backend_gtk3cairo import (FigureCanvasGTK3Cairo
                                                   as FigureCanvas)
from matplotlib.figure import Figure
import numpy as np

from npl import __config__
from npl.fileio import RSFHandler
# from npl.drawer import SpectrumFigure


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
        self.figure.ax.cla()
        self.figure.plot_spectra(self.app.s_container)
        self.figure.plot_rsf(self.rsf["elements"], self.rsf["source"])
        self.figure.canvas.draw_idle()
        if not keepaxes:
            pass
        self.figure.recenter_view()

    def on_show_rsf(self, *_ignore):
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
            self.refresh()
        dialog.destroy()

    def on_select_energyrange(self):
        """Calls the plotter energy range selector method."""
        self.figure.get_span()


class BeautifulFigure(Figure):
    """A customized canvas."""
    def __init__(self):
        # pylint: disable=invalid-name
        super().__init__(figsize=(10, 10), dpi=80)
        self.canvas = FigureCanvas(self)
        self.ax = self.add_axes([0, 0, 1, 1])

        self.now_xy = [0, 0, 1, 1]
        self.s_xy = [np.inf, -np.inf, np.inf, -np.inf]

    def set_ticks(self):
        """Configures axes ticks."""
        self.axes.tick_params(reset=True,
                              axis="both",
                              direction="in",
                              pad=-20,
                              labelsize="large",
                              labelleft=False)
        if self.s_xy[0] == np.inf:
            self.axes.tick_params(which="both",
                                  bottom=False,
                                  top=False,
                                  left=False,
                                  right=False,
                                  labelbottom=False)

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

    def plot_spectra(self, container):
        """Plots a spectrum."""
        if container:
            self.s_xy = [np.inf, -np.inf, np.inf, -np.inf]
        for spectrum in container:
            if spectrum["Visibility"] == "default":
                self.ax.plot(spectrum["Energy"], spectrum["Intensity"],
                             label=spectrum["Name"], c="k", lw=1)
                self.s_xy = [min(self.s_xy[0], min(spectrum["Energy"])),
                             max(self.s_xy[1], max(spectrum["Energy"])),
                             min(self.s_xy[2], min(spectrum["Intensity"])),
                             max(self.s_xy[3], max(spectrum["Intensity"]
                                                   * 1.05))]

    def get_span(self):
        """Makes a SpanSelector and uses it."""
        pass

    def plot_rsf(self, elements, source):
        """Plots RSF values for a certain element with given X-ray souce."""
        if not elements:
            return
        peakdata = []
        for element in elements:
            peaks = self.rsfhandler.get_element(element, source)
            peakdata.append(peaks)

        max_rsf = max(max([[(x["RSF"] + 1e-9) for x in dicts]
                           for dicts in peakdata]))
        normfactor = (self.now_xy[3] / max_rsf * 0.8)
        colorcycle = "gbrcmy"*10
        for i, peaks in enumerate(peakdata):
            for peak in peaks:
                if peak["RSF"] == 0:
                    rsf = 0.5 * self.now_xy[3]
                else:
                    rsf = peak["RSF"] * normfactor
                self.ax.vlines(peak["BE"], 0, rsf, colors=colorcycle[i], lw=2)
                self.ax.annotate(peak["Fullname"],
                                 xy=[peak["BE"], rsf + self.now_xy[3] * 0.015],
                                 color="blue",
                                 textcoords="data")


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
        self.parent.refresh_canvas()
        self.push_current()
        self._update_view()



class SelectElementsDialog(Gtk.Dialog):
    """Lets the user select elements and a source for rsf plotting."""
    sources = ["Al", "Mg"]
    def __init__(self, parent, default_elements=None, default_source=None):
        super().__init__("Element Library", parent, 0,
                         ("_Cancel", Gtk.ResponseType.CANCEL,
                          "_OK", Gtk.ResponseType.OK))
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
        rowbox1.pack_start(Gtk.Label("Source", width_chars=15),
                           False, False, 10)
        rowbox1.pack_start(self.source_combo, True, True, 10)
        rowbox2 = Gtk.Box()
        rowbox2.pack_start(Gtk.Label("Elements", width_chars=15),
                           False, False, 10)
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
