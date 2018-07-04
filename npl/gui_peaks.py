"""Provides a widget that shows detailed information on and provides
interation with peaks of a given region."""
# pylint: disable=wrong-import-position

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


PEAK_TITLES = {
    "fwhm": "FWHM",
    "center": "Position",
    "name": "Name",
    "area": "Area"}


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

        self.view = PeakView(
            self, peaks=self.region.peaks,
            attrs=["name", "center", "fwhm", "area"])
        scrollable = Gtk.ScrolledWindow()
        scrollable.set_property("min-content-height", 100)
        scrollable.add(self.view)
        self.pack_start(scrollable, True, True, 0)

        self.psettings = PeakControl(self, peak=None)
        self.pack_start(self.psettings, False, False, 0)

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
        rembutton.connect("clicked", self.remove_peaks)

        buttonbox = Gtk.Box()
        buttonbox.pack_start(fitbutton, False, False, 0)
        buttonbox.pack_start(Gtk.Label("Peaks"), True, True, 0)
        buttonbox.pack_start(addbutton, False, False, 0)
        buttonbox.pack_start(rembutton, False, False, 0)
        return buttonbox

    def remove_peaks(self, *_ignore):
        """Removes peak."""
        peaks = self.view.get_selected_peaks()
        for peak in peaks:
            self.region.remove_peak(peak)


class PeakView(Gtk.TreeView):
    """Treeview that displays Peak details."""
    def __init__(self, manager, peaks, attrs):
        super().__init__()
        self.manager = manager
        self.peaks = peaks
        self.attrs = attrs
        self.model = self.make_model()
        self.sortable_model = Gtk.TreeModelSort(self.model)

        self.set_model(self.sortable_model)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_rules_hint(True)

        self.connect("button-press-event", self.on_row_clicked)

        self.make_columns()

    def refresh(self):
        """Refreshes the view."""
        self.model = self.make_model()
        self.sortable_model = Gtk.TreeModelSort(self.model)
        self.set_model(self.sortable_model)
        # self.make_columns()

    def make_model(self):
        """Makes a ListStore and fills it with data, returns the model."""
        types = [str] * len(self.attrs)
        model = Gtk.ListStore(*types)
        for peak in self.peaks:
            row = []
            for attr in self.attrs:
                value = getattr(peak, attr)
                if isinstance(value, float):
                    row.append("{:.2f}".format(value))
                elif isinstance(value, int):
                    row.append(str(value))
                else:
                    row.append(value)
            model.append(row)
        return model

    def make_columns(self):
        """Makes columns."""
        for i, attr in enumerate(self.attrs):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(PEAK_TITLES[attr], renderer, text=i)
            column.set_resizable(True)
            column.set_reorderable(True)
            self.append_column(column)

    def get_selected_peaks(self):
        """Returns list of currently selected Peak objects."""
        _model, pathlist = self.get_selection().get_selected_rows()
        peaks = []
        for path in pathlist:
            index = path.get_indices()[0]
            peaks.append(self.peaks[index])
        return peaks

    def on_row_clicked(self, treeview, event):
        """Callback for context menu."""
        posx = int(event.x)
        posy = int(event.y)
        pathinfo = treeview.get_path_at_pos(posx, posy)
        if pathinfo is None:
            return True
        path, _col, _cellx, _celly = pathinfo
        peak = self.peaks[path.get_indices()[0]]
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.manager.psettings.set_peak(peak)
            return path in self.get_selection().get_selected_rows()[1]


class PeakControl(Gtk.ListBox):
    """Makes methods for setting constraints etc available to the user."""
    def __init__(self, manager, peak):
        super().__init__()
        self.manager = manager
        self.peak = peak
        self.build()

    def build(self):
        """Builds the box."""
        if self.peak is None:
            return
        row = self.get_name_row()
        self.add(row)
        for attr in ["center", "fwhm", "area"]:
            row = self.get_min_max_expr_row(attr)
            self.add(row)
        self.show_all()

    def get_name_row(self):
        """Row for setting the peak name."""
        def callback(entry):
            """Callback for the entry."""
            self.peak.name = entry.get_text()
            self.manager.view.refresh()
        label = Gtk.Label("Name", width_chars=15)
        entry = Gtk.Entry(text=self.peak.name)
        entry.connect("activate", callback)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox.pack_start(label, False, False, 10)
        hbox.pack_start(entry, True, True, 10)
        row = Gtk.ListBoxRow()
        row.add(hbox)
        return row

    def get_min_max_expr_row(self, attr):
        """Returns a ListBoxRow that includes setting min/max value, actual
        value, whether to vary and an expression for peak.attr."""
        def min_callback(entry):
            """Callback for the entry."""
            self.peak.set_constraints(attr, min=float(entry.get_text()))
        def max_callback(entry):
            """Callback for the entry."""
            self.peak.set_constraints(attr, max=float(entry.get_text()))
        def expr_callback(entry):
            """Callback for the entry."""
            self.peak.set_constraints(attr, expr=entry.get_text())
        label = Gtk.Label(PEAK_TITLES[attr], width_chars=10)
        min_entry = Gtk.Entry(text=self.peak.get_constraint(attr, "min"),
                              width_chars=3)
        min_entry.connect("activate", min_callback)
        max_entry = Gtk.Entry(text=self.peak.get_constraint(attr, "max"),
                              width_chars=3)
        max_entry.connect("activate", max_callback)
        expr_entry = Gtk.Entry(text=self.peak.get_constraint(attr, "expr"),
                               width_chars=5)
        expr_entry.connect("activate", expr_callback)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(min_entry, True, True, 0)
        hbox.pack_start(max_entry, True, True, 0)
        hbox.pack_start(expr_entry, True, True, 0)
        row = Gtk.ListBoxRow()
        row.add(hbox)
        return row

    def set_peak(self, peak):
        """Changes the peak to display."""
        self.peak = peak
        self.clear()
        self.build()

    def clear(self):
        """Removes all widgets."""
        for widget in self.get_children():
            self.remove(widget)
