"""Provides a widget that shows detailed information on and provides
interaction with regions of a given spectrum."""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from npl.gui_peaks import PeakManager


class RegionManager(Gtk.Box):
    """Has a header and allows for adding regions and displays them."""
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.parent = parent
        # self.notebook = RegionNotebook(self)
        self.stack = RegionsUI(self.parent.app, [])

        # self.set_spectrum = self.notebook.set_spectrum
        # self.get_selected_region = self.notebook.get_selected_region

        self.add(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        add_img = Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON)
        rem_img = Gtk.Image.new_from_icon_name(
            "list-remove", Gtk.IconSize.BUTTON)
        self.addbutton = Gtk.Button(None, image=add_img)
        self.addbutton.connect("clicked", self.parent.do_create_region)
        self.rembutton = Gtk.Button(None, image=rem_img)
        def delete_region_callback(*_ignore):
            """Callback for button to remove region."""
            self.stack.delete_region()
        self.rembutton.connect("clicked", delete_region_callback)

        buttonbox = Gtk.Box()
        buttonbox.pack_start(Gtk.Label("Regions"), True, True, 0)
        buttonbox.pack_start(self.addbutton, False, False, 0)
        buttonbox.pack_start(self.rembutton, False, False, 0)

        self.add(buttonbox)
        # self.add(self.notebook)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)
        self.add(stack_switcher)
        self.add(self.stack)
        self.show_all()

    def set_spectrum(self, spectrum):
        if spectrum is None:
            self.stack.set_regions([])
            return
        self.stack.set_regions(spectrum.regions)

    def set_spectra(self, spectra):
        """Sets the spectra for which regions are displayed."""
        pass

    def set_selected_region(self, region):
        """Sets which region is now selected."""
        pass

    def get_selected_region(self):
        """Returns selected region."""
        return self.stack.get_selected_region()


class RegionsUI(Gtk.Stack):
    """A box containing region specific UI, meant for a Gtk.Stack or
    Gtk.Notebook."""
    def __init__(self, app, regions):
        super().__init__()
        self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.set_transition_duration(500)

        self.app = app
        self.regions = regions
        self.build()

    def build(self):
        """Builds stack parts."""
        for region in self.regions:
            box = SingleRegionUI(self.app, region)
            self.add_titled(box, str(region.sid), region.name)
        self.show_all()

    def set_regions(self, regions):
        """Rebuilds with new regions."""
        for child in self.get_children():
            if child.region not in regions:
                self.remove(child)
        old_regions = (child.region for child in self.get_children())
        for region in regions:
            if region not in old_regions:
                box = SingleRegionUI(self.app, region)
                self.add_titled(box, str(region.sid), region.name)
        self.show_all()

    def delete_region(self):
        """Deletes currently selected region."""
        region = self.get_selected_region()
        self.remove(self.get_visible_child())
        region.spectrum.remove_region(region)
        self.show_all()

    def get_selected_region(self):
        """Returns selected region."""
        return self.get_visible_child().region

    def set_selected_region(self, region):
        """Sets selection to region."""
        self.set_visible_child_name(str(region.sid))


class SingleRegionUI(Gtk.Box):
    """UI element for a single region."""
    def __init__(self, app, region):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.region = region
        self.pmanager = PeakManager(parent=self.app.win, region=self.region)
        self.pack_start(self.get_energy_box(), False, False, 0)
        self.pack_start(self.get_bgtype_box(), False, False, 0)
        self.pack_start(self.pmanager, True, True, 0)

    def get_energy_box(self):
        """Returns a box for viewing and editing the energy boundaries of the
        region."""
        def callback(entry):
            """Callback for energy setting."""
            energies = re.findall(r"\d+\.\d+|\d+", entry.get_text())
            self.region.set(emin=float(energies[0]), emax=float(energies[1]))

        entry = Gtk.Entry(
            text="{:.2f} - {:.2f}".format(self.region.emin, self.region.emax))
        entry.connect("activate", callback)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(Gtk.Label("Energy", width_chars=15), False, False, 2)
        box.pack_start(entry, True, True, 2)
        return box

    def get_bgtype_box(self):
        """Returns a box for setting the background type in this region."""
        def callback(combo):
            """Callback for background type setting."""
            self.region.set(bgtype=combo.get_active_text())

        combo = Gtk.ComboBoxText()
        combo.set_entry_text_column(0)
        for i, bgtype in enumerate(self.region.bgtypes):
            combo.append_text(bgtype)
            if bgtype == self.region.bgtype:
                combo.set_active(i)
        combo.connect("changed", callback)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(
            Gtk.Label("Background Type", width_chars=15), False, False, 2)
        box.pack_start(combo, True, True, 2)
        return box


# class RegionNotebook(Gtk.Notebook):
#     """Includes all the widgets for region/peak settings."""
#     def __init__(self, rmanager, spectrum=None):
#         super().__init__()
#         self.spectrum = spectrum
#         self.rmanager = rmanager
#         self.set_scrollable(True)
#         self.popup_enable()
#         self.build()
#
#     def build(self):
#         """Makes a page for each region."""
#         if self.spectrum is None or not self.spectrum.regions:
#             self.hide()
#             return
#
#         for region in self.spectrum.regions:
#             page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
#
#             getset = RegionGetSet(region)
#             pview = PeakManager(self.rmanager.parent, region=region)
#             page.pack_start(getset, False, False, 0)
#             page.pack_start(pview, True, True, 0)
#
#             pagelabel = Gtk.Label(str(region.name))
#             self.append_page(page, pagelabel)
#         self.show_all()
#
#     def get_selected_region(self):
#         """Returns selected region."""
#         page_num = self.get_current_page()
#         return self.spectrum.regions[page_num]
#
#     def remove_region(self, *_ignore):
#         """Deletes currently selected region."""
#         region = self.get_selected_region()
#         self.spectrum.remove_region(region)
#         self.clear()
#         self.build()
#
#     def clear(self):
#         """Clears the Notebook."""
#         while self.get_n_pages() > 0:
#             self.remove_page(-1)
#
#     def set_spectrum(self, spectrum):
#         """Sets the spectrum to work with."""
#         self.spectrum = spectrum
#         self.clear()
#         self.build()


# class RegionGetSet(Gtk.Box):
#     """A Box with entries that allows for changing values of a given region.
#     Also has title labels and has an apply method."""
#     def __init__(self, region):
#         super().__init__(orientation=Gtk.Orientation.VERTICAL)
#         self.region = region
#         self.add_energy_setting()
#         self.add_background_type()
#
#     def add_energy_setting(self):
#         """Adds a box for viewing and editing the energy boundaries of the
#         region."""
#         def callback(entry):
#             """Callback for energy setting."""
#             energies = re.findall(r"\d+\.\d+|\d+", entry.get_text())
#             self.region.set(emin=float(energies[0]), emax=float(energies[1]))
#
#         entry = Gtk.Entry(
#             text="{:.2f} - {:.2f}".format(self.region.emin, self.region.emax))
#         entry.connect("activate", callback)
#
#         box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
#         box.pack_start(Gtk.Label("Energy", width_chars=15), False, False, 2)
#         box.pack_start(entry, True, True, 2)
#         self.pack_start(box, False, False, 2)
#
#     def add_background_type(self):
#         """Adds a box for setting the background type in this region."""
#         def callback(combo):
#             """Callback for background type setting."""
#             self.region.set(bgtype=combo.get_active_text())
#
#         combo = Gtk.ComboBoxText()
#         combo.set_entry_text_column(0)
#         for i, bgtype in enumerate(self.region.bgtypes):
#             combo.append_text(bgtype)
#             if bgtype == self.region.bgtype:
#                 combo.set_active(i)
#         combo.connect("changed", callback)
#
#         box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
#         box.pack_start(
#             Gtk.Label("Background Type", width_chars=15), False, False, 2)
#         box.pack_start(combo, True, True, 2)
#         self.pack_start(box, False, False, 2)
