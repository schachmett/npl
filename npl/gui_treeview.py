"""Provides a custom Gtk.Treeview for viewing spectrum metadata and
filtering/sorting/selecting them."""
# pylint: disable=wrong-import-position

import re

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk


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
        self.model = SpectrumModelContainerIface(container=container,
                                                 keys=container.keys)
        self.filter_model = self.model.filter_new()
        self.sortable_model = Gtk.TreeModelSort(self.filter_model)
        self.menu = None

        self.set_model(self.sortable_model)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_rules_hint(True)

        self.filter = (None, None)
        self.filter_model.set_visible_func(self.filter_func)

        self.connect("button-press-event", self.on_row_clicked)

        if titles is None:
            used_keys = ["Name", "Notes", "Sweeps", "DwellTime", "PassEnergy"]
            self.titles = [(key, container.titles[key]) for key in used_keys]
        else:
            self.titles = titles
        self.make_columns()

    def title2key(self, title):
        """Returns the corresponding key to a given column title."""
        for (key, title_) in self.titles:
            if title_ == title:
                return key
        return None

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
            if self.menu is not None:
                self.menu.popup(None, None, None, None,
                                event.button, event.time)
            return path in self.get_selection().get_selected_rows()[1]
        # pylint: disable=protected-access
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.menu.do_first()
            return True

    def make_columns(self):
        """Makes columns with given titles."""
        def render_text(_col, renderer, model, iter_, key):
            """Renders a cell in column with value from that
            model column which number in model_col_indexes corresponds
            to title."""
            col_index = self.model.get_column_from_key(key)
            value = model.get_value(iter_, col_index)
            renderer.set_property("text", str(value))
        for i, (key, title) in enumerate(self.titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_cell_data_func(renderer, render_text, key)
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
                self.keys = []

    def get_spectrum(self, path):
        """Returns the spectrum for iter_or_path."""
        if isinstance(path, Gtk.TreeIter):
            path = self.get_path(path)
        index = path.get_indices()[0]
        return self.container[index]

    def get_value_by_key(self, iter_, key):
        """Returns the value by iter_ and key."""
        spectrum = self.container.get_spectrum_by_sid(iter_.user_data)
        value = spectrum.get(key)
        return value

    def get_column_from_key(self, key):
        """Returns the column for a given key."""
        column = self.keys.index(key)
        return column

    def do_get_value(self, iter_, column):
        """Returns the value for iter_ and column."""
        key = self.keys[column]
        value = self.get_value_by_key(iter_, key)
        return str(value)

    def do_get_iter(self, path):
        """Returns a new TreeIter that points at path.
        The implementation returns a 2-tuple (bool, TreeIter|None).
        """
        indices = path.get_indices()
        iter_ = Gtk.TreeIter()
        if indices[0] < len(self.container):
            iter_.user_data = self.container[indices[0]].sid
            return (True, iter_)
        return (False, None)

    def do_iter_next(self, iter_):
        """Returns an iter pointing to the next row or None.
        The implementation returns a 2-tuple (bool, TreeIter|None).
        """
        if self.container:
            if iter_ is not None:
                oldpath = self.container.get_idx_by_sid(iter_.user_data)
                if oldpath is None or len(self.container) <= oldpath + 1:
                    return (False, None)
                if len(self.container) > oldpath + 1:
                    iter_.user_data = self.container[oldpath + 1].sid
            else:
                iter_.user_data = self.container[0].sid
            return (True, iter_)
        return (False, None)

    def do_iter_has_child(self, _iter_):
        """True if iter_ has children."""
        return False

    def do_iter_nth_child(self, iter_, child_n):
        """Return iter that is set to the nth child of iter_."""
        if iter_ is None and child_n < len(self.container):
            iter_ = Gtk.TreeIter()
            iter_.user_data = self.container[child_n].sid
            return (True, iter_)
        return (False, None)

    def do_get_path(self, iter_):
        """Returns tree path references by iter_."""
        if iter_ is not None:
            sid = iter_.user_data
            idx = self.container.get_idx_by_sid(sid)
            if idx is None:
                return None
            path = Gtk.TreePath((idx, ))
            return path
        return None

    def do_iter_children(self, iter_):
        """Returns if iter has been set to the first child and that iter."""
        if iter_ is not None or not self.container:
            iter_.user_data = None
            return (False, iter_)
        iter_.user_data = self.container[0].sid
        return (True, iter_)

    def do_iter_n_children(self, iter_):
        """Returns number of children of iter_."""
        if iter_ is not None:
            return 0
        return len(self.container)

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


class SpectrumModelContainerIface(SpectrumModel):
    """A TreeModel providing the methods to "talk" with a SpectrumContainer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container.bind(self, "container_callback")

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
        if not self.keys:
            self.keys = spectrum.essential_keys
        path = (self.container.index(spectrum), )
        iter_ = self.get_iter(path)
        self.row_inserted(path, iter_)

    def remove(self, iter_):
        """Removes row with iter_."""
        if iter_ is not None:
            path = self.get_path(iter_)
            self.row_deleted(path)

    def amend(self, spectrum):
        """Changes a model row."""
        path = (self.container.index(spectrum), )
        iter_ = self.get_iter(path)
        self.remove(iter_)
        self.append(spectrum)

    def clear(self):
        """Removes every row."""
        for idx in range(len(self.container)):
            iter_ = self.get_iter((idx, ))
            self.remove(iter_)


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
    def __init__(self, sview, actions):
        self.sview = sview
        self.doubleclick_action = None
        super().__init__()
        self.actions = list(actions)
        for (name, class_, callback) in self.actions:
            action = Gtk.MenuItem(name)
            self.append(action)
            action.connect("activate", getattr(class_, callback))
            action.show()

    def add_action(self, name, class_, callback):
        """Adds another action to the menu."""
        self.actions.append((name, class_, callback))
        for (_name, _class_, _callback) in self.actions:
            action = Gtk.MenuItem(_name)
            self.append(action)
            action.connect("activate", getattr(_class_, _callback))
            action.show()

    def do_action(self, callback):
        """Calls a given callback."""
        for (_name, _class_, _callback) in self.actions:
            if _callback == callback:
                getattr(_class_, _callback)()
                return

    def set_doubleclick_action(self, name, class_, callback):
        """Sets the action to do for double clicking an item."""
        if (name, class_, callback) not in self.actions:
            self.add_action(name, class_, callback)
        self.doubleclick_action = callback

    def do_first(self):
        """Executes the first action."""
        if self.doubleclick_action:
            callback = self.doubleclick_action
        else:
            callback = self.actions[0][2]
        self.do_action(callback)
