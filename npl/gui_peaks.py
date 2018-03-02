"""Provides a widget that shows detailed information on and provides
interation with peaks of a given region."""
# pylint: disable=wrong-import-position

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class PeakManager(Gtk.Box):
    """This class combines all functionality regarding peaks and makes them
    accessible as Gtk.Box."""
    def __init__(self, parent, region):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent = parent
        self.region = region

        self.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        headerbox = self.build_header()
        self.add(headerbox)
        databox = self.build_peakdata()
        self.add(databox)

    def build_header(self):
        """Builds the header row containing "Peaks" title and buttons."""
        def call_fit(*_ignore):
            """Button callback for region fit."""
            self.region.fit()
        fitbutton = Gtk.Button(label="Fit")
        fitbutton.connect("clicked", call_fit)
        add_img = Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        addbutton = Gtk.Button(None, image=add_img)
        addbutton.connect("clicked", self.parent.do_create_peak)
        rem_img = Gtk.Image.new_from_icon_name(
            "list-remove", Gtk.IconSize.BUTTON)
        rembutton = Gtk.Button(None, image=rem_img)
        rembutton.connect("clicked", self.remove_peak)

        buttonbox = Gtk.Box()
        buttonbox.pack_start(fitbutton, False, False, 0)
        buttonbox.pack_start(Gtk.Label("Peaks"), True, True, 0)
        buttonbox.pack_start(addbutton, False, False, 0)
        buttonbox.pack_start(rembutton, False, False, 0)
        return buttonbox

    def build_peakdata(self):
        """Builds single peak boxes and combines them."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        headstring = "{:<15}{:>10}{:>10}{:>10}".format(
            "Name", "Center", "Height", "FWHM")
        box.pack_start(Gtk.Label(headstring), True, True, 0)
        for peak in self.region.peaks:
            row = self.build_peakrow(peak)
            box.add(row)
        return box

    @staticmethod
    def build_peakrow(peak):
        """Makes a horizontal Box for a specific peak."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        peakstring = "{:<15}{:>10.2f}{:>10.2f}{:>10.2f}".format(
            peak.name, peak.center, peak.height, peak.fwhm)
        row.pack_start(Gtk.Label(peakstring), True, True, 0)
        return row

    def remove_peak(self, peak):
        """Removes peak."""
        pass
