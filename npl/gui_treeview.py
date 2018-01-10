"""Provides a custom Gtk.Treeview for viewing spectrum metadata and
filtering/sorting/selecting them."""
# pylint: disable=wrong-import-position

import re
import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Gdk, GdkPixbuf

from npl import __config__


class ContainerView(Gtk.TreeView):
    """Treeview that connects to the SpectrumModel, is filterable and
    spawns a SpectrumContextMenu on right click. Also triggers
    show_selected on double click."""
    # TODO: make reorderable work (for dragging/dropping list items)
    # treeview.set_reorderable(True)
    # treeview.connect("drag_data_received", self.on_test)
    def __init__(self, container, attrs=None):
        super().__init__()
        self.model = ContainerModelIface(container=container,
                                         attrs=container.spectrum_attrs)
        self.filter_model = self.model.filter_new()
        self.sortable_model = Gtk.TreeModelSort(self.filter_model)
        self.menu = None

        self.set_model(self.sortable_model)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.set_rules_hint(True)
        # self.set_headers_visible(False)     # hide column names

        self.filter = (None, None)
        self.filter_model.set_visible_func(self.filter_func)

        self.connect("button-press-event", self.on_row_clicked)

        if attrs is None:
            attrs = ["name", "notes", "sweeps", "dwelltime", "passenergy"]
        self.titles = [(attr, container.title(attr)) for attr in attrs]
        self.make_columns()

    def title2attr(self, title):
        """Returns the corresponding key to a given column title."""
        for (attr, title_) in self.titles:
            if title_ == title:
                return attr
        return None

    def get_selected_spectra(self):
        """Returns list of currently selected Spectrum objects."""
        _model, pathlist = self.get_selection().get_selected_rows()
        spectra = []
        for path in pathlist:
            spectra.append(self.model.get_spectrum(path))
        return spectra

    def set_selected_spectra(self, spectra):
        """Sets selection to given spectra."""
        self.get_selection().unselect_all()
        for spectrum in spectra:
            path = self.model.container.index(spectrum)
            self.get_selection().select_path(path)

    def filter_by(self, attr, search_term):
        """Filters the treeview: only show rows where
        spectrum[key] matches regex."""
        self.filter = (attr, search_term)
        self.filter_model.refilter()

    def filter_func(self, model, iter_, _data):
        """Matches the regex with spectrum[key]."""
        attr, search_term = self.filter
        regex = re.compile(r".*{}.*".format(search_term), re.IGNORECASE)
        if attr is None or not search_term:
            return True
        spectrum = model.get_spectrum(iter_)
        return re.match(regex, getattr(spectrum, attr))

    def on_row_clicked(self, treeview, event):
        """Callback for button-press-event, popups the menu on right click
        and calls show_selected for double left click. Return value
        determines if the selection on self persists."""
        posx = int(event.x)
        posy = int(event.y)
        pathinfo = treeview.get_path_at_pos(posx, posy)
        if pathinfo is None:
            return True
        path, _col, _cellx, _celly = pathinfo
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if self.menu is not None:
                self.menu.popup(None, None, None, None,
                                event.button, event.time)
            return path in self.get_selection().get_selected_rows()[1]
        # pylint: disable=protected-access
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.menu.do_doubleclick()
            return True

    def make_columns(self):
        """Makes columns with given titles."""
        def render_text(_col, renderer, model, iter_, attr):
            """Renders a cell in column with value from that
            model column which number in model_col_indexes corresponds
            to title."""
            col_index = self.model.get_column_from_attr(attr)
            value = model.get_value(iter_, col_index)
            renderer.set_property("text", str(value))
        for i, (attr, title) in enumerate(self.titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_cell_data_func(renderer, render_text, attr)
            col_index = self.model.get_column_from_attr(attr)
            column.set_sort_column_id(col_index)
            column.set_resizable(True)
            column.set_reorderable(True)
            self.append_column(column)


class ContainerModel(GObject.GObject, Gtk.TreeModel):
    """A TreeModel that reflects a spectrum container."""
    # pylint: disable=no-self-use
    def __init__(self, container, attrs=None):
        super().__init__()
        self.container = container
        if self.container:
            if attrs is not None:
                self.attrs = [attr for attr in attrs
                              if attr in self.container[0].attrs]
            else:
                self.attrs = self.container[0].attrs
        else:
            if attrs is not None:
                self.attrs = attrs
            else:
                self.attrs = []

    def get_spectrum(self, path):
        """Returns the spectrum for iter_or_path."""
        if isinstance(path, Gtk.TreeIter):
            path = self.get_path(path)
        index = path.get_indices()[0]
        return self.container[index]

    def get_value_by_attr(self, iter_, attr):
        """Returns the value by iter_ and attribute."""
        spectrum = self.container.get_spectrum_by_sid(iter_.user_data)
        value = getattr(spectrum, attr)
        return value

    def get_column_from_attr(self, attr):
        """Returns the column for a given attribute."""
        column = self.attrs.index(attr)
        return column

    def do_get_value(self, iter_, column):
        """Returns the value for iter_ and column."""
        attr = self.attrs[column]
        value = self.get_value_by_attr(iter_, attr)
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
                oldpath = self.container.get_idx_by_sid(iter_.user_data)[0]
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
            idx = self.container.get_idx_by_sid(sid)[0]
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
        return len(self.attrs)

    def do_get_column_type(self, _column):
        """Returns the type of the column."""
        return str

    def do_get_flags(self):
        """Returns the flags supported by this interface."""
        return Gtk.TreeModelFlags.ITERS_PERSIST#, Gtk.TreeModelFlags.LIST_ONLY


class ContainerModelIface(ContainerModel):
    """A TreeModel providing the methods to "talk" with a SpectrumContainer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container.subscribe(self.container_callback)

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

    def append(self, spectrum, path=None, iter_=None):
        """Adds a spectrum to the model."""
        if not self.attrs:
            self.attrs = self.container.spectrum_attrs
        if path is None:
            path = (self.container.index(spectrum), )
        if iter_ is None:
            iter_ = self.get_iter(path)
        self.row_inserted(path, iter_)

    def remove(self, iter_):
        """Removes row with iter_."""
        if iter_ is not None:
            path = self.get_path(iter_)
            self.row_deleted(path)

    def amend(self, spectrum):
        """Changes a model row."""
        iter_ = Gtk.TreeIter()
        iter_.user_data = spectrum.sid
        # path = Gtk.TreePath((self.container.index(spectrum), ))
        # iter_ = self.get_iter(path)
        self.remove(iter_)
        self.append(spectrum)#, path=path, iter_=iter_)

    def clear(self):
        """Removes every row."""
        for idx in range(len(self.container)):
            iter_ = self.get_iter((idx, ))
            self.remove(iter_)


class SpectrumSettings(Gtk.Box):
    """A box with settings for single spectra."""
    # pylint: disable=attribute-defined-outside-init
    def __init__(self, parent, spectra=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.spectra = spectra
        self.refresh_canvas = parent.refresh_canvas
        self.build()

    def build(self):
        """Builds elements."""
        self.add_smoothing_setting()
        self.add_norm_button()
        self.connect_all_signals(self.apply)
        self.connect_all_signals(self.refresh_canvas)
        self.show_all()

    def clear(self):
        """Clears box."""
        for child in self.get_children():
            self.remove(child)

    def add_smoothing_setting(self):
        """Adds a box for setting smoothness of the spectrum."""
        adj = Gtk.Adjustment(0, 0, 40, 2, 2, 0)
        self.smoothscale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        self.smoothscale.set_digits(0)
        self.smoothscale.set_hexpand(True)
        if not self.spectra:
            self.smoothscale.set_range(0, 0)
        else:
            self.smoothscale.set_range(0, 40)
            self.smoothscale.set_value(self.spectra[0].smoothness)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(
            Gtk.Label(" Smoothing", width_chars=15, xalign=0), False, True, 2)
        box.pack_start(self.smoothscale, True, True, 2)
        self.pack_start(box, False, False, 2)

    def add_norm_button(self):
        """Adds a box for norming the spectrum."""
        icon_path = os.path.join(
            __config__.get("general", "basedir"), "icons/divide16.png")
        norm_img = Gtk.Image.new_from_file(icon_path)
        self.normbutton = Gtk.Button(label=" Normalize", image=norm_img)
        self.normbutton.set_always_show_image(True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(self.normbutton, False, False, 2)
        self.pack_start(box, False, False, 2)


    def connect_all_signals(self, func):
        """Connects all active elements with given function."""
        # self.smoothentry.connect("activate", func)
        self.normbutton.connect("clicked", func)
        self.smoothscale.connect("value-changed", func)

    def apply(self, *_ignore):
        """Applies changes to spectra."""
        if self.spectra:
            for spectrum in self.spectra:
                # spectrum.smoothness = int(self.smoothentry.get_text())
                spectrum.smoothness = int(self.smoothscale.get_value())

    def set_spectra(self, spectra):
        """Sets the spectra to work with."""
        self.spectra = spectra
        self.clear()
        self.build()


class TreeViewFilterBar(Gtk.Box):
    """A filter bar featuring an entry and a combobox determining which field
    to search."""
    def __init__(self, sview, default_colname=None, hide_combo=False,
                 hide_icon=False):
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

        if not hide_combo:
            self.pack_start(self.combo, False, False, 2)
        if not hide_icon:
            icon_path = os.path.join(
                __config__.get("general", "basedir"), "icons/search.svg")
            iconbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path, 24, -1, True)
            icon = Gtk.Image.new_from_pixbuf(iconbuf)
            self.pack_start(icon, False, False, 2)
        self.pack_start(self.entry, True, True, 2)

    def on_entry_changed(self, entry):
        """Applies a new filter when the entry is changed."""
        title = self.combo.get_active_text()
        attr = self.sview.title2attr(title)
        search_term = entry.get_text()
        self.sview.filter_by(attr, search_term)


class ContainerContextMenu(Gtk.Menu):
    """Context menu for actions that depend on giving a selection of
    spectra."""
    def __init__(self, sview, actions):
        self.sview = sview
        self.doubleclick_action = None
        super().__init__()
        self.actions = list(actions)
        for (name, callback) in self.actions:
            action = Gtk.MenuItem(name)
            self.append(action)
            action.connect("activate", callback)
            action.show()

    def add_action(self, name, callback):
        """Adds another action to the menu."""
        self.actions.append((name, callback))
        action = Gtk.MenuItem(name)
        self.append(action)
        action.connect("activate", callback)
        action.show()

    def do_action(self, callback):
        """Calls a given callback."""
        for (_name, _callback) in self.actions:
            if _callback == callback:
                callback()
                return

    def set_doubleclick_action(self, name, callback):
        """Sets the action to do for double clicking an item."""
        if (name, callback) not in self.actions:
            self.add_action(name, callback)
        self.doubleclick_action = callback

    def do_doubleclick(self):
        """Executes the first action."""
        if self.doubleclick_action:
            callback = self.doubleclick_action
        else:
            callback = self.actions[0][1]
        self.do_action(callback)
