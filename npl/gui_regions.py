"""Provides a widget that shows detailed information on a given spectrum,
including regions and peak fits."""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class RegionManager(Gtk.Notebook):
    """Includes all the widgets for region/peak settings."""
    def __init__(self, parent, spectrum=None):
        super().__init__()
        self.spectrum = spectrum
        self.parent = parent
        self.set_scrollable(True)
        self.popup_enable()
        self.build_pages()

    def build_pages(self):
        """Makes a page for each region."""
        self.clear()
        if self.spectrum is None or not self.spectrum.regions:
            self.hide()
            return

        for region in self.spectrum.regions:
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            getset = RegionGetSet(region)
            getset.bgcombo.connect("changed", getset.apply)
            getset.bgcombo.connect("changed", self.refresh_gui)
            getset.energy_entry.connect("activate", getset.apply)
            getset.energy_entry.connect("activate", self.refresh_gui)
            apply_button = Gtk.Button.new_with_label("Apply")
            apply_button.connect("clicked", getset.apply)
            apply_button.connect("clicked", self.refresh_gui)
            getset.pack_start(apply_button, False, False, 2)
            page.pack_start(getset, False, False, 0)
            self.append_page(page, Gtk.Label(str(region.name)))
        self.show_all()

    def refresh_gui(self, *_ignore):
        """Refreshes main window components and the RegionManager itself after
        changing region attributes."""
        self.parent.refresh_all()

    def clear(self):
        """Clears the Notebook."""
        for i in range(self.get_n_pages() + 1):
            self.remove_page(i)

    def set_spectrum(self, spectrum):
        """Sets the spectrum to work with."""
        self.spectrum = spectrum
        self.build_pages()


# class UIGetSet(Gtk.Box):
#     """A Box with an entry that allows for changing values of a given object.
#     Also has title labels and has an apply method."""
#     def __init__(self, obj):
#         super().__init__(orientation=Gtk.Orientation.VERTICAL)
#         self.obj = obj
#         self.entries = {}
#
#     def attr_box(self, attrs, title=None):
#         """Adds a box for a given attribute."""
#         if title is None:
#             title = attrs[0]
#         box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
#         label = Gtk.Label(title, width_chars=15)
#         box.pack_start(label, False, False, 2)
#         for attr in attrs:
#             entry = Gtk.Entry(text=getattr(self.obj, attr))
#             box.pack_start(entry, True, True, 2)
#             self.entries[attr] = entry
#         return box
#
#     def apply(self):
#         """Applies changes to obj."""
#         for i, attr in enumerate(self.attrs):
#             setattr(self.obj, attr, self.entries[attr].get_text)


class RegionGetSet(Gtk.Box):
    """A Box with entries that allows for changing values of a given region.
    Also has title labels and has an apply method."""
    def __init__(self, region):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.region = region
        self.add_energy_box()
        self.add_background_type()

    def add_energy_box(self):
        """Adds a box for viewing and editing the energy boundaries of the
        region."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(Gtk.Label("Energy", width_chars=15), False, False, 2)
        self.energy_entry = Gtk.Entry(text="{:.2f} - {:.2f}"
                                           "".format(self.region.emin,
                                                     self.region.emax))
        box.pack_start(self.energy_entry, False, False, 2)
        self.pack_start(box, False, False, 2)

    def add_background_type(self):
        """Adds a box for setting the background type in this region."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(Gtk.Label("Background Type", width_chars=15),
                       False, False, 2)
        self.bgcombo = Gtk.ComboBoxText()
        self.bgcombo.set_entry_text_column(0)
        for i, bgtype in enumerate(self.region.bgtypes):
            self.bgcombo.append_text(bgtype)
            if bgtype == self.region.bgtype:
                self.bgcombo.set_active(i)
        box.pack_start(self.bgcombo, False, False, 2)
        self.pack_start(box, False, False, 2)

    def apply(self, *_ignore):
        """Applies changes to the region."""
        energies = re.findall(r"\d+\.\d+|\d+", self.energy_entry.get_text())
        self.region.emin = float(energies[0])
        self.region.emax = float(energies[1])
        self.region.bgtype = self.bgcombo.get_active_text()
