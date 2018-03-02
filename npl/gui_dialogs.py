"""Dialogs for use in other modules."""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango

class EditSpectrumDialog(Gtk.Dialog):
    """Shows a dialog with entries to change metadata, needs a parent and
    a list of spectra."""
    excluding_key = " (multiple)"

    def __init__(self, parent, spectra, attrs=None):
        super().__init__(
            "Settings",
            parent,
            0,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK))
        if not spectra:
            self.response(Gtk.ResponseType.CANCEL)
            return
        self.set_size_request(300, -1)
        okbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.OK)
        okbutton.set_can_default(True)
        okbutton.grab_default()

        self.spectra = spectra
        self.entries = []
        self.multiple = len(spectra) > 1
        self.box = self.get_content_area()
        if attrs is None:
            attrs = sorted(list(self.spectra[0].titles.keys()))
        self.titles = [(attr, spectra[0].title(attr)) for attr in attrs]

        self.build_window()
        self.show_all()

    def build_window(self):
        """Creates the labels and entries and orders them."""
        fnamebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        fname_title_label = Gtk.Label(
            label="Filename(s):", width_chars=15, xalign=0)

        fnames = ""
        for spectrum in self.spectra:
            fnames += spectrum.fname + "\n"
        fnames = fnames.strip()
        fnames_label = Gtk.Label(
            label=fnames, wrap=True, max_width_chars=45,
            wrap_mode=Pango.WrapMode.CHAR)

        fnamebox.pack_start(fname_title_label, False, False, 10)
        fnamebox.pack_start(fnames_label, False, False, 10)

        self.box.pack_start(fnamebox, False, False, 5)
        for (attr, title) in self.titles:
            self.box.pack_start(
                self.generate_entry(attr, title), False, False, 2)

    def generate_entry(self, attr, title):
        """Makes an entry with a specific title for a spectrum key."""
        if not self.multiple:
            value = str(getattr(self.spectra[0], attr))
        else:
            values = []
            for spectrum in self.spectra:
                values.append(str(getattr(spectrum, attr)))
            value = " | ".join(set(values)) + self.excluding_key

        label = Gtk.Label(label=title, width_chars=15, xalign=0)
        entry = Gtk.Entry(text=value, width_chars=45)
        entry.set_activates_default(True)
        self.entries.append(entry)

        rowbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rowbox.pack_start(label, False, False, 10)
        rowbox.pack_start(entry, False, False, 10)
        return rowbox

    def change_values(self):
        """Actually changes the values of the spectra."""
        for spectrum in self.spectra:
            for i, (attr, _) in enumerate(self.titles):
                new_value = self.entries[i].get_text()
                if self.excluding_key not in new_value:
                    setattr(spectrum, attr, new_value)


class AskForSaveDialog(Gtk.Dialog):
    """Asks if you are sure to quit/make new file without saving."""
    def __init__(self, parent):
        super().__init__("Save current file?", parent, 0,
                         ("_Cancel", Gtk.ResponseType.CANCEL,
                          "_No", Gtk.ResponseType.NO,
                          "_Yes", Gtk.ResponseType.YES))
        yesbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.YES)
        yesbutton.set_can_default(True)
        yesbutton.grab_default()
        self.box = self.get_content_area()
        text = Gtk.Label("Save changes to current project?")
        self.box.pack_start(text, True, True, 10)
        self.show_all()


class SimpleFileFilter(Gtk.FileFilter):
    """Simpler FileFilter for FileChooserDialogs with better constructor."""
    def __init__(self, name, patterns):
        """ filter for file chooser dialogs """
        super().__init__()
        for pattern in patterns:
            self.add_pattern(pattern)
        self.set_name(name)


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
        self.elements_entry.set_activates_default(True)

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
        return elements, source


class GetCalibrationDialog(Gtk.Dialog):
    """Lets the user select a region where the maximum is detected, then
    the user can project this maximum to a given energy value, resulting
    in a calibration value."""
    def __init__(self, parent, spectra):
        super().__init__(
            "Semi-automatic calibration", parent,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK))
        okbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.OK)
        okbutton.set_can_default(True)
        okbutton.grab_default()
        self.set_modal(False)

        self.box = self.get_content_area()
        self.spectra = spectra
        self.parent = parent

        self.getspan_button = Gtk.Button(label="Get span")
        self.calfrom_label = Gtk.Label("Select a peak", width_chars=10)
        self.calto_entry = Gtk.Entry(text="", width_chars=6)

        self.getspan_button.connect("clicked", self.get_span)
        self.calfrom = []

        rowbox = Gtk.Box()
        rowbox.pack_start(self.getspan_button, False, False, 2)
        rowbox.pack_start(self.calfrom_label, False, False, 2)
        rowbox.pack_start(self.calto_entry, False, False, 2)
        rowbox.pack_start(Gtk.Label("eV", width_chars=2), False, False, 2)
        self.box.pack_start(rowbox, False, False, 0)
        self.show_all()

    def get_span(self, _widget):
        """Gets the span from which the maximum is taken."""
        self.calfrom = []
        def span_callback(emin, emax):
            """Callback for SpanSelector."""
            span = (emin, emax)
            for spectrum in self.spectra:
                self.calfrom.append(spectrum.get_energy_at_maximum(span))
            if len(set(self.calfrom)) <= 1:
                self.calfrom_label.set_text(
                    "{:.2f} eV ->".format(self.calfrom[0]))
            else:
                self.calfrom_label.set_text("multiple")
        self.parent.do_get_span(span_callback)

    def get_calibration(self):
        """Returns the actual calibration value."""
        calto = float(self.calto_entry.get_text())
        if self.calfrom:
            calibration = []
            for i, spectrum in enumerate(self.spectra):
                calibration.append(
                    calto - self.calfrom[i] + spectrum.calibration)
            return calibration
        return None
