"""Provides a widget that shows detailed information on a given spectrum,
including regions and peak fits."""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class RegionManager(Gtk.Box):
    """Has a header and allows for adding regions and displays them."""
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent = parent
        self.notebook = RegionNotebook()
        self.set_spectrum = self.notebook.set_spectrum

        self.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        add_img = Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        rem_img = Gtk.Image.new_from_icon_name(
            "list-remove", Gtk.IconSize.BUTTON)
        self.addbutton = Gtk.Button(None, image=add_img)
        self.addbutton.connect("clicked", self.parent.do_create_region)
        self.rembutton = Gtk.Button(None, image=rem_img)
        self.rembutton.connect("clicked", self.notebook.remove_region)
        buttonbox = Gtk.Box()
        buttonbox.pack_start(Gtk.Label("Regions"), True, True, 0)
        buttonbox.pack_start(self.addbutton, False, False, 0)
        buttonbox.pack_start(self.rembutton, False, False, 0)

        self.add(buttonbox)
        self.add(self.notebook)

        self.set_size_request(-1, 200)


class RegionNotebook(Gtk.Notebook):
    """Includes all the widgets for region/peak settings."""
    def __init__(self, spectrum=None):
        super().__init__()
        self.spectrum = spectrum
        self.set_scrollable(True)
        self.popup_enable()
        self.build()

    def build(self):
        """Makes a page for each region."""
        if self.spectrum is None or not self.spectrum.regions:
            self.hide()
            return

        for region in self.spectrum.regions:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            getset = RegionGetSet(region)
            page.pack_start(getset, False, False, 0)

            pagelabel = Gtk.Label(str(region.name))
            self.append_page(page, pagelabel)
        self.show_all()

    def remove_region(self, *_ignore):
        """Deletes currently selected region."""
        page_num = self.get_current_page()
        self.spectrum.regions.remove(self.spectrum.regions[page_num])
        self.clear()
        self.build()

    def clear(self):
        """Clears the Notebook."""
        while self.get_n_pages() > 0:
            self.remove_page(-1)

    def set_spectrum(self, spectrum):
        """Sets the spectrum to work with."""
        self.spectrum = spectrum
        self.clear()
        self.build()


class RegionGetSet(Gtk.Box):
    """A Box with entries that allows for changing values of a given region.
    Also has title labels and has an apply method."""
    def __init__(self, region):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.region = region
        self.add_energy_setting()
        self.add_background_type()

    # def connect_all_signals(self, func):
    #     """Connects all active elements with given function."""
    #     self.energy_entry.connect("activate", func)
    #     self.bgcombo.connect("changed", func)

    def add_energy_setting(self):
        """Adds a box for viewing and editing the energy boundaries of the
        region."""
        def callback(entry):
            """Callback for energy setting."""
            energies = re.findall(r"\d+\.\d+|\d+", entry.get_text())
            self.region.emin = float(energies[0])
            self.region.emax = float(energies[1])

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(Gtk.Label("Energy", width_chars=15), False, False, 2)
        self.energy_entry = Gtk.Entry(
            text="{:.2f} - {:.2f}".format(self.region.emin, self.region.emax))
        self.energy_entry.connect("activate", callback)
        box.pack_start(self.energy_entry, True, True, 2)
        self.pack_start(box, False, False, 2)

    def add_background_type(self):
        """Adds a box for setting the background type in this region."""
        def callback(combo):
            """Callback for background type setting."""
            self.region.bgtype = combo.get_active_text()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(
            Gtk.Label("Background Type", width_chars=15), False, False, 2)
        self.bgcombo = Gtk.ComboBoxText()
        self.bgcombo.set_entry_text_column(0)
        for i, bgtype in enumerate(self.region.bgtypes):
            self.bgcombo.append_text(bgtype)
            if bgtype == self.region.bgtype:
                self.bgcombo.set_active(i)
        self.bgcombo.connect("changed", callback)
        box.pack_start(self.bgcombo, True, True, 2)
        self.pack_start(box, False, False, 2)

    # def apply(self, *_ignore):
    #     """Applies changes to the region."""
    #     energies = re.findall(r"\d+\.\d+|\d+", self.energy_entry.get_text())
    #     self.region.emin = float(energies[0])
    #     self.region.emax = float(energies[1])
    #     self.region.bgtype = self.bgcombo.get_active_text()
