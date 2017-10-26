"""this module manages the windows of npl"""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk

from npl.containers import Spectrum


class SpectrumView(Gtk.TreeView):
    """Treeview that connects to the SpectrumModel, is filterable and
    spawns a SpectrumContextMenu on right click. Also triggers
    show_selected on double click."""
#   To do: make reorderable work (for dragging/dropping list items)
#   treeview.set_reorderable(True)
#   treeview.connect("drag_data_received", self.on_test)
    def __init__(self, container, titles=None, app=None):
        super().__init__()
        self.app = app
        self.model = SpectrumModel(container)
        self.filter_model = self.model.filter_new()
        self.sortable_model = Gtk.TreeModelSort(self.filter_model)
        self.menu = SpectrumContextMenu(self, app=self.app)

        self.set_model(self.model)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_rules_hint(True)

        self.filter = (None, None)
        self.filter_model.set_visible_func(self.filter_func)

        self.connect("button-press-event", self.on_row_clicked)

        if titles is None:
            self.titles = [("Name", "Name"),    # list of (key, title)s
                           ("Notes", "Notes"),
                           ("Sweeps", "Sweeps"),
                           ("DwellTime", "Dwell [s]"),
                           ("PassEnergy", "Pass [eV]")]
        else:
            self.titles = titles
        self.make_columns()


    def get_selected_spectra(self):
        """Returns list of currently selected Spectrum objects."""
        _model, pathlist = self.get_selection().get_selected_rows()
        spectra = []
        for path in pathlist:
            spectra.append(self.model.get_spectrum(path))
        return spectra

    def filter_by(self, key, search_term):
        """Filters the treeview: only show rows where
        spectrum[key] matches regex."""
        self.filter = (key, search_term)
        self.filter_model.refilter()

    def filter_func(self, model, iter_, _data):
        """Matches the regex with spectrum[key]."""
        key, search_term = self.filter
        regex = re.compile(r".*{}.*".format(search_term), re.IGNORECASE)
        if key is None or not search_term:
            return True
        spectrum = model.get_spectrum(iter_)
        return re.match(regex, spectrum[key])

    def on_row_clicked(self, treeview, event):
        """Callback for button-press-event, popups the menu on right click
        and calls show_selected for double left click. Return value
        determines if the selection on self persists."""
        posx = int(event.x)
        posy = int(event.y)
        pathinfo = treeview.get_path_at_pos(posx, posy)
        if pathinfo is None:
            return
        path, _col, _cellx, _celly = pathinfo
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup(None, None, None, None, event.button, event.time)
            return path in self.get_selection().get_selected_rows()[1]
        # pylint: disable=protected-access
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            print("show selected")
            return True

    def make_columns(self):
        """Makes columns with given titles."""
        def text_rendering(_col, renderer, model, iter_, key):
            """Renders a cell in column with value from that
            model column which number in model_col_indexes corresponds
            to title."""
            col_index = self.model.get_column_from_key(key)
            print(type(iter_), type(col_index))
            value = model.get_value(iter_, col_index)
            renderer.set_property("text", str(value))
        cellfunc = text_rendering
        for i, (key, title) in enumerate(self.titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_cell_data_func(renderer, cellfunc, key)
            col_index = self.model.get_column_from_key(key)
            column.set_sort_column_id(col_index)
            column.set_resizable(True)
            column.set_reorderable(True)
            self.append_column(column)


class SpectrumModel(GObject.GObject, Gtk.TreeModel):
    """A TreeModel that reflects a spectrum container."""
    # pylint: disable=no-self-use
    def __init__(self, container, keys=None):
        super().__init__()
        self.container = container
        if self.container:
            if keys is not None:
                self.keys = [key for key in keys if key in self.container[0]]
            else:
                self.keys = list(self.container[0].keys())
        else:
            if keys is not None:
                self.keys = keys
            else:
                self.keys = Spectrum.essential_keys
        self.container.bind(self, "container_callback")

    def get_spectrum(self, iter_or_path):
        """Returns the spectrum for iter_or_path."""
        if isinstance(iter_or_path, Gtk.TreeIter):
            index = iter_or_path.user_data
        else:
            index = iter_or_path.get_indices()[0]
        return self.container[index]

    def get_container_value(self, iter_, key_or_column):
        """Returns the value by iter_ and key or column."""
        if isinstance(key_or_column, int):
            key = self.keys[key_or_column]
        else:
            key = key_or_column
        value = self.container[iter_.user_data][key]
        return value

    def get_column_from_key(self, key):
        """Returns the column for a given key."""
        column = self.keys.index(key)
        return column

    def do_get_value(self, iter_, column):
        """Returns the value for iter_ and column."""
        # if
        key = self.keys[column]
        value = self.container[iter_.user_data][key]
        return str(value)

    def container_callback(self, keyword, **kwargs):
        """Manages signals from the spectrum container."""
        if keyword == "append":
            spectrum = kwargs["spectrum"]
            self.append(spectrum)
        elif keyword == "remove":
            idx = kwargs["index"]
            iter_ = self.get_iter(idx)
            self.remove(iter_)
        elif keyword == "clear":
            self.clear()
        elif keyword == "amend":
            spectrum = kwargs["spectrum"]
            # key = kwargs["key"]
            # value = kwargs["value"]
            self.amend(spectrum)

    def append(self, spectrum):
        """Adds a spectrum to the model."""
        path = (self.container.index(spectrum), )
        iter_ = self.get_iter(path)
        self.row_inserted(path, iter_)

    def remove(self, iter_):
        """Removes row with iter_."""
        if iter_:
            path = self.get_path(iter_)
            self.row_deleted(path)

    def amend(self, spectrum):
        """Changes a model row."""
        iter_ = self.get_iter(self.container.index(spectrum))
        self.remove(iter_)
        self.append(spectrum)

    def clear(self):
        """Removes every row."""
        # iter_ = self.get_iter_first()
        # iters = [iter_, ]
        # while iter_ is not None:
        #     iter_ = self.iter_next(iter_)
        #     iters.append(iter_)
        # for iter_ in iters[:-1]:
        #     self.remove(iter_)
        for idx in range(len(self.container)):
            iter_ = self.get_iter(idx)
            print(iter_.user_data)
            self.remove(iter_)

    def do_get_iter(self, path):
        """Returns a new TreeIter that points at path.
        The implementation returns a 2-tuple (bool, TreeIter|None).
        """
        if isinstance(path, Gtk.TreePath):
            indices = path.get_indices()
        else:
            indices = [path]
        print(indices)
        if indices[0] < len(self.container):
            iter_ = Gtk.TreeIter()
            iter_.user_data = indices[0]
            return (True, iter_)
        return (False, None)

    def do_iter_next(self, iter_):
        """Returns an iter pointing to the next column or None.
        The implementation returns a 2-tuple (bool, TreeIter|None).
        """
        if iter_.user_data is None and self.container:
            iter_.user_data = 0
            return (True, iter_)
        if iter_.user_data < len(self.container) - 1:
            iter_.user_data += 1
            return (True, iter_)
        return (False, None)

    def do_iter_has_child(self, _iter_):
        """True if iter_ has children."""
        return False

    def do_iter_nth_child(self, iter_, child_n):
        """Return iter that is set to the nth child of iter_."""
        # We've got a flat list here, so iter_ is always None and the
        # nth child is the row.
        if iter_ is None:
            iter_ = Gtk.TreeIter()
            iter_.user_data = child_n
            return (True, iter_)
        return (False, None)

    def do_get_path(self, iter_):
        """Returns tree path references by iter_."""
        if iter_.user_data is not None:
            path = Gtk.TreePath((iter_.user_data,))
            return path
        return None

    def do_iter_children(self, iter_):
        """Returns if iter has been set to the first child and that iter."""
        if not iter_.user_data is None and self.container:
            iter_.user_data = 0
            return (True, iter_)
        return (False, None)

    def do_iter_n_children(self, iter_):
        """Returns number of children of iter_."""
        return len(self.container) if iter_ is None else 0

    def do_iter_parent(self, _child):
        """Returns parent of child."""
        return None

    def do_get_n_columns(self):
        """Returns the number of columns."""
        return len(self.keys)

    def do_get_column_type(self, _column):
        """Returns the type of the column."""
        return str

    def do_get_flags(self):
        """Returns the flags supported by this interface."""
        return Gtk.TreeModelFlags.ITERS_PERSIST, Gtk.TreeModelFlags.LIST_ONLY


class TreeViewFilterBar(Gtk.Box):
    """A filter bar featuring an entry and a combobox determining which field
    to search."""
    def __init__(self, sview, default_colname=None):
        super().__init__(Gtk.Orientation.HORIZONTAL, spacing=2)
        self.set_size_request(-1, 30)
        self.sview = sview

        self.combo = Gtk.ComboBoxText()
        self.combo.set_entry_text_column(0)
        for i, column in enumerate(self.sview.get_columns()):
            title = column.get_title()
            self.combo.append_text(title)
            if title == default_colname:
                self.combo.set_active(i)

        self.entry = Gtk.Entry()
        self.entry.connect("changed", self.on_entry_changed)

        self.pack_start(self.combo, False, False, 0)
        self.pack_start(self.entry, True, True, 0)

    def on_entry_changed(self, entry):
        """Applies a new filter when the entry is changed."""
        title = self.combo.get_active_text()
        key = self.sview.title2key(title)
        search_term = entry.get_text()
        self.sview.filter_by(key, search_term)

class SpectrumContextMenu(Gtk.Menu):
    """Context menu for actions that depend on giving a selection of
    spectra."""
    def __init__(self, sview, app=None):
        self.sview = sview
        self.app = app
        super().__init__()
        actions = (("Show selected", print),
                   ("Foo", print))
        for (name, callback) in actions:
            action = Gtk.MenuItem(name)
            self.append(action)
            action.connect("activate", callback)
            action.show()
