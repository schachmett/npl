#!/usr/bin/env python3
"""this module manages the windows of npl"""

import os
import sys
import re
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import db_manager
import plotter as my_plotter
from containers import Spectrum, SpectrumContainer

CODEDIR = os.path.dirname(os.path.realpath(__file__))
BASEDIR = "/home/simon/npl/.npl"
WIN_XSIZE = 1200
WIN_YSIZE = 700


def main():
    """main shit"""
    dbm = db_manager.DBHandler("npl.db")
    dbm.wipe_tables()
    cont = SpectrumContainer(dbm)

    parser = db_manager.FileParser()
    prs = list()
    datafname = ("/home/simon/Dokumente/uni/julian_themann_ba/"
                 "Au111-growth_Mg.txt")
    prs.extend(parser.parse_spectrum_file(datafname))
    for par in prs:
        spec = Spectrum(par)
        cont.append(spec)

    app = Npl(cont)
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


class Npl(Gtk.Application):
    """application class"""
    def __init__(self, container):
        super().__init__(application_id="org.npl.app",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        GLib.set_application_name("NPL")
        self.s_container = container
        self.win = None

        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "cmd test", None)

    def do_activate(self, **_ignore):
        """activates window?"""
        self.win = MainWindow(app=self, container=self.s_container)
        self.win.show_all()

    def do_startup(self, **_ignore):
        """startup stuff, for now only menu bar"""
        Gtk.Application.do_startup(self)

        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.do_new)
        self.add_action(new_action)
        add_action = Gio.SimpleAction.new("add_spectrum", None)
        add_action.connect("activate", self.do_add_spectrum)
        self.add_action(add_action)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.do_quit)
        self.add_action(quit_action)

        builder = Gtk.Builder.new_from_file(os.path.join(CODEDIR, "gtk/menus.ui"))
        self.set_menubar(builder.get_object("menubar"))
#         self.set_app_menu(builder.get_object("appmenu"))

    def do_command_line(self, command_line, **_ignore):
        """handles command line arguments"""
        options = command_line.get_options_dict()
        if options.contains("test"):
            print("Test argument received")
        self.activate()
        return 0

    def do_new(self, _action, _param):
        """start new project"""
        pass

    def do_add_spectrum(self, _action, _param):
        """imports a spectrum file"""
        pass

    def do_quit(self, _action, _param):
        """quit"""
        self.quit()


class MainWindow(Gtk.ApplicationWindow):
    """main window composed mainly of treeview and mpl canvas"""
    def __init__(self, app, container):
        super().__init__(title="NPL", application=app)
        self.set_size_request(WIN_XSIZE, WIN_YSIZE)
        self.set_icon_from_file(os.path.join(BASEDIR, "icons/logo.svg"))

        self.s_container = container
        self.sview = SpectrumView(self, self.s_container)
        self.cvs = Canvas(self, self.s_container)
        self.build_window()

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.do_about)
        self.add_action(about_action)
        show_selected_action = Gio.SimpleAction.new("show_selected", None)
        show_selected_action.connect("activate", self.do_show_selected)
        self.add_action(show_selected_action)

    def build_window(self):
        """do gtk boxing stuff"""
        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        contentpanes = Gtk.HPaned()
        contentpanes.shrink = False
        self.add(masterbox)
        masterbox.pack_start(contentpanes, True, True, 0)
        contentpanes.pack1(self.sview, False, False)
        contentpanes.pack2(self.cvs, True, False)

    def reload_treeview(self):
        """treeview reads its data again"""
        self.sview.reload_()

    def refresh_canvas(self, keepaxes=False):
        """plotter refetches its info"""
        self.cvs.refresh(keepaxes)

    def do_about(self, _action, _param):
        """show about dialog"""
        aboutdialog = Gtk.AboutDialog()
        aboutdialog.set_transient_for(self)
        authors = ["Simon Fischer <sfischer@ifp.uni-bremen.de>"]
        aboutdialog.set_program_name("NPL")
        aboutdialog.set_authors(authors)
        aboutdialog.set_license_type(Gtk.License.GPL_3_0)
        aboutdialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(BASEDIR, "icons/logo.svg"),
            50, -1, True))
        aboutdialog.connect("response", self.on_close)
        aboutdialog.show()

    def do_show_selected(self, action, param):
        print("hey")

    def on_close(self, action, _parameter):
        """closes the action (e.g. dialog)"""
        action.destroy()


class ToolBar(Gtk.Toolbar):
    """main toolbar for file operations"""
    def __init__(self):
        pass

    def add_file(self):
        """uses parser and appends spectrum to the container"""
        pass

    def delete_spectra(self):
        """deletes spectrum from the container"""
        pass

    def load_project(self):
        """gets container from db file"""
        pass

    def save_project(self):
        """saves container to db file"""
        pass


class AnalBar():
    """toolbar above the canvas for analyzing the data"""
    def __init__(self):
        pass

    def show_rsf(self):
        """show the orbitals from database"""
        pass

    def background(self):
        """switches background on and off"""
        pass


class SpectrumView(Gtk.Box):
    """treeview containing spectrum information"""
    col_keys = ["Name", "Notes", "Sweeps", "DwellTime", "PassEnergy"]
    col_titles = ["Name", "Notes", "Sweeps", "Dwell [s]", "Pass [eV]"]
    maincol = col_titles.index("Notes")

    def __init__(self, mainwindow, container):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.mainwindow = mainwindow
        self.s_container = container
        self.liststore = self.create_model()
        self.current_filter = None
        self.menu = self.build_context_menu()

        treeview = self.build_treeview()
        scrollable = Gtk.ScrolledWindow()
        scrollable.set_property("min-content-width", 300)
        scrollable.add(treeview)
        filterbar = self.build_filterbar()
        self.pack_start(scrollable, True, True, 0)
        self.pack_start(filterbar, False, False, 0)

    def create_model(self):
        """create liststore and load it with the given spectrum keys as well as
        the spectrum itself"""
        number_of_cols = len(self.col_keys)
        types = [str, ] * number_of_cols + [object]
        self.liststore = Gtk.ListStore(*types)
        for spectrum in self.s_container:
            row = [str(spectrum[key]) for key in self.col_keys] + [spectrum]
            self.liststore.append(row)
        self.filter_model = self.liststore.filter_new()
        self.filter_model.set_visible_func(self.spectrum_filter_func)
        sorted_model = Gtk.TreeModelSort(self.filter_model)
#         self.sorted_model.connect("rows-reordered", self.reload_)
        return sorted_model

    def append(self, spectrum):
        row = [str(spectrum[key]) for key in self.col_keys] + [spectrum]
        self.liststore.append(row)

#     def reload_(self, *_ignore):        # broken!
#         """reloads the entire liststore"""
#         print("reload!")
#         iter_ = self.liststore.get_iter_first()
#         iter2_ = self.sorted_model.get_iter_first()
#         i = 1
#         while iter_ is not None:
#             spectrum = self.liststore[iter_][-1]
#             print("next")
#             print(spectrum["Sweeps"])
#             newrow = [str(spectrum[key]) for key in self.col_keys] + [spectrum]
#             print(newrow[2])
#             self.liststore.set_row(iter_, newrow)
#             if self.liststore.iter_next(iter_) is not None:
#                 iter2_ = self.sorted_model.get_iter(i)
#                 print(self.sorted_model[iter2_][2])
#             iter_ = self.liststore.iter_next(iter_)
#             i += 1
#         n = 0
#         while True:
#             col = self.treeview.get_column(n)
#             if col is None:
#                 break
#             col.set_sort_column_id(n)
#             n += 1

#         self.liststore.clear()
#         for spectrum in self.s_container:
#             row = [str(spectrum[key]) for key in self.col_keys] + [spectrum]
#             self.liststore.append(row)
#             print(spectrum["Sweeps"])

#     def refill(self, container):
#         """fills in another given container into the liststore"""
#         self.s_container = container
#         self.reload_()

    def build_treeview(self):
        """does gtk building stuff"""
        self.model = self.create_model()
        treeview = Gtk.TreeView.new_with_model(self.model)
        self.selection = treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        treeview.set_rules_hint(True)
        treeview.connect("button-press-event", self.on_row_clicked)
        for i, col_title in enumerate(self.col_titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            column.set_cell_data_func(renderer, self.populate_cell, col_title)
            column.set_sort_column_id(i)
            column.set_resizable(True)
            column.set_reorderable(True)
            treeview.append_column(column)
        return treeview

    def populate_cell(self, _col, renderer, treemodel, iter_, col_title):
        """renders the cell from a spectrum object"""
        col_key = self.col_keys[self.col_titles.index(col_title)]
        value = treemodel[iter_][-1][col_key]
        renderer.set_property("text", str(value))

    def build_filterbar(self):
        """builds the widget on the bottom for filtering the entries"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_size_request(-1, 30)
        criterion_combo = Gtk.ComboBoxText()
        criterion_combo.set_entry_text_column(0)
        for colname in self.col_titles:
            criterion_combo.append_text(colname)
        criterion_combo.set_active(self.maincol)
        criterion_entry = Gtk.Entry()
        criterion_entry.connect("changed", self.on_filter_criterion_changed,
                                criterion_combo)
        box.pack_start(criterion_combo, False, False, 0)
        box.pack_start(criterion_entry, True, True, 0)
        return box

    def spectrum_filter_func(self, model, iter_, _data):
        """returns true for entries that should still show"""
        if self.current_filter is None:
            return True
        else:
            col_index = self.current_filter[0]
            search_term = self.current_filter[1]
            regex = re.compile(r".*{0}.*".format(search_term), re.IGNORECASE)
            return re.match(regex, model[iter_][col_index])

    def build_context_menu(self):
        menu = Gtk.Menu()
        show_selected_action = Gtk.MenuItem("Show selected")
        menu.append(show_selected_action)
        show_selected_action.connect("activate", self.on_show_selected)
        show_selected_action.show()
        edit_action = Gtk.MenuItem("Edit spectrum")
        menu.append(edit_action)
        edit_action.connect("activate", self.on_edit_spectrum)
        edit_action.show()
        return menu

    def on_show_selected(self, *_action):
        model, pathlist = self.selection.get_selected_rows()
        spectra = []
        for path in pathlist:
            iter_ = model.get_iter(path)
            spectra.append(model[iter_][-1])
        self.s_container.show_only(spectra)
        self.mainwindow.refresh_canvas(keepaxes=False)

    def on_edit_spectrum(self, _action):
        model, pathlist = self.selection.get_selected_rows()
        spectra = []
        for path in pathlist:
            iter_ = model.get_iter(path)
            spectra.append(model[iter_][-1])
        dialog = EditSpectrumDialog(self.mainwindow, spectra)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            user_input = dialog.get_user_input()
            for spectrum in spectra:
                for key, value in user_input:
                    if dialog.excluding_key not in value and value is not "":
                        spectrum[key] = value
        dialog.destroy()

    def on_filter_criterion_changed(self, entry, combo):
        """applies new filter"""
        col_title = combo.get_active_text()
        search_term = entry.get_text()
        if col_title is None or len(search_term) == 0:
            self.current_filter = None
        else:
            col_index = self.col_titles.index(col_title)
            self.current_filter = (col_index, search_term)
        self.filter_model.refilter()

    def on_row_clicked(self, treeview, event):
        """context menu for amending spectrum and for
        double click -> plot single"""
        posx = int(event.x)
        posy = int(event.y)
        pathinfo = treeview.get_path_at_pos(posx, posy)
        if pathinfo is not None:
            path, _col, _cellx, _celly = pathinfo
        else:
            return
        iter_ = self.liststore.get_iter(path)
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup(None, None, None, None, event.button, event.time)
            return path in self.selection.get_selected_rows()[1]
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.on_show_selected()
            return True


class EditSpectrumDialog(Gtk.Dialog):
    """shows a dialog with entries to change metadata"""
    excluding_key = " (multiple)"
    spectrum_keys = SpectrumView.col_keys
    spectrum_titles = SpectrumView.col_titles
    
    def __init__(self, parent, spectra):
        super().__init__("Settings", parent, 0,
                         (Gtk.STOCK_CANCEL,
                          Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_OK,
                          Gtk.ResponseType.OK))
        self.set_size_request(500, -1)
        okbutton = self.get_widget_for_response(response_id=Gtk.ResponseType.OK)
        okbutton.set_can_default(True)
        okbutton.grab_default()
        self.spectra = spectra
        self.entries = list()
        if len(spectra) == 1:
            self.multiple = False
        else:
            self.multiple = True

        self.box = self.get_content_area()
        fnamebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        fname_title_label = Gtk.Label(label="Filename(s):", width_chars=15)
        fnames = "\n".join(list(str(spectrum["Filename"]) for spectrum in self.spectra))
        fnames_label = Gtk.Label(label=fnames)
        fnamebox.pack_start(fname_title_label, False, False, 10)
        fnamebox.pack_start(fnames_label, True, True, 10)
        self.box.pack_start(fnamebox, False, False, 5)
        for key in SpectrumView.col_keys:
            self.box.pack_start(self.generate_entry(key), False, False, 2)
        self.show_all()

    def generate_entry(self, key):
        if not self.multiple:
            value = str(self.spectra[0][key])
        else:
            values = []
            for spectrum in self.spectra:
                values.append(str(spectrum[key]))
            value = " | ".join(set(values)) + self.excluding_key
        labelstring = self.spectrum_titles[self.spectrum_keys.index(key)]
        rowbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(label=labelstring, width_chars=15)
        entry = Gtk.Entry(text=value)
        entry.set_activates_default(True)
        self.entries.append(entry)
        rowbox.pack_start(label, False, False, 10)
        rowbox.pack_start(entry, True, True, 10)
        return rowbox

    def get_user_input(self):
        user_input = list()
        for spectrum in self.spectra:
            for i, key in enumerate(self.spectrum_keys):
                user_input.append((key, self.entries[i].get_text()))
        return user_input


class Canvas(Gtk.Box):
    """plotting area"""
    def __init__(self, mainwindow, container):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.mainwindow = mainwindow
        self.s_container = container
        self.plotter = my_plotter.Plotter()

        navbar = MPLNavBar(self.plotter, self.mainwindow)
        self.pack_start(self.plotter.get_canvas(), True, True, 0)
        self.pack_start(navbar, False, False, 0)

        self.refresh()

    def refresh(self, keepaxes=False):
        """redraws canvas"""
        self.plotter.plot(self.s_container, keepaxes)

    def refill(self, container):
        """feeds the plotter another container"""
        self.s_container = container
        self.refresh()


class MPLNavBar(NavigationToolbar2GTK3):
    """navbar for the canvas"""
    def __init__(self, plotter, mainwindow):
        self.plotter = plotter
        self.mainwindow = mainwindow
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
        super().__init__(self.plotter.get_canvas(), self.mainwindow)

    def fit_view(self, _event):
        """centers the view to plotted graphs"""
        if self._views.empty():
            self.push_current()
        self.plotter.recenter_view()
        self.mainwindow.refresh_canvas()
        self.push_current()
        self._update_view()


if __name__ == "__main__":
    main()
