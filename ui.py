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

    def do_activate(self):
        """activates window?"""
        self.win = MainWindow(app=self, container=self.s_container)
        self.win.show_all()

    def do_startup(self):
        """startup stuff, for now only menu bar"""
        Gtk.Application.do_startup(self)

        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.do_new)
        self.add_action(new_action)
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.do_about)
        self.add_action(about_action)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.do_quit)
        self.add_action(quit_action)

        builder = Gtk.Builder.new_from_file(os.path.join(CODEDIR, "menus.ui"))
        self.set_menubar(builder.get_object("menubar"))
#         self.set_app_menu(builder.get_object("appmenu"))

    def do_command_line(self, command_line):
        """handles command line arguments"""
        options = command_line.get_options_dict()
        if options.contains("test"):
            print("Test argument received")
        self.activate()
        return 0

    def do_new(self, _action, _param):
        pass

    def do_about(self, _action, _param):
        aboutdialog = Gtk.AboutDialog()
        aboutdialog.set_transient_for(self.win)
        authors = ["Simon Fischer <sfischer@ifp.uni-bremen.de>"]
        aboutdialog.set_program_name("NPL")
        aboutdialog.set_authors(authors)
        aboutdialog.set_license_type(Gtk.License.GPL_3_0)
        aboutdialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(BASEDIR, "icons/logo.svg"),
            50, -1, True))
        aboutdialog.connect("response", self.on_close)
        aboutdialog.show()

    def do_quit(self, _action, _param):
        self.quit()

    def on_close(self, action, _parameter):
        action.destroy()


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

    def build_window(self):
        """do gtk boxing stuff"""
        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        contentpanes = Gtk.HPaned()
        contentpanes.shrink = False
        self.add(masterbox)
        masterbox.pack_start(contentpanes, True, True, 0)
        contentpanes.pack1(self.sview, False, False)
        contentpanes.pack2(self.cvs, True, False)

    def refresh_treeview(self):
        """treeview reads its data again"""
        self.sview.refresh()

    def refresh_canvas(self, keepaxes=False):
        """plotter refetches its info"""
        self.cvs.refresh(keepaxes)


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
    colnames = {"Name": "Name", "Notes": "Notes", "Sweeps": "Sweeps",
                "DwellTime": "Dwell [s]", "PassEnergy": "Pass [eV]"}
    used_cols = ["Name", "Notes", "Sweeps", "DwellTime", "PassEnergy"]
    used_titles = ["Name", "Notes", "Sweeps", "Dwell [s]", "Pass [eV]"]

    def __init__(self, mainwindow, container):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.mainwindow = mainwindow
        self.s_container = container
        self.liststore = Gtk.ListStore(str, str, str, str, str, object)
        self.current_filter = None
        builder = Gtk.Builder.new_from_file(os.path.join(CODEDIR, "menus.ui"))
        self.menu = Gtk.Menu.new_from_model(builder.get_object("treeview_menu"))

        scrollable_treeview = self.build_treeview()
        filterbar = self.build_filterbar()
        self.pack_start(scrollable_treeview, True, True, 0)
        self.pack_start(filterbar, False, False, 0)

        self.refresh()

    def build_treeview(self):
        """does gtk building stuff"""
        self.filter_ = self.liststore.filter_new()
        self.filter_.set_visible_func(self.spectrum_filter_func)
        treeview = Gtk.TreeView.new_with_model(self.filter_)
        treeview.set_rules_hint(True)
        treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        treeview.connect("button-press-event", self.on_row_clicked)
        for i, column_title in enumerate(self.used_titles):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_resizable(True)
            treeview.append_column(column)
        scrollable_treelist = Gtk.ScrolledWindow()
        scrollable_treelist.set_property("min-content-width", 300)
        scrollable_treelist.add(treeview)
        return scrollable_treelist

    def build_filterbar(self):
        """builds the widget on the bottom for filtering the entries"""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_size_request(-1, 30)
        criterion_combo = Gtk.ComboBoxText()
        criterion_combo.set_entry_text_column(0)
        for colname in self.used_titles:
            criterion_combo.append_text(colname)
        criterion_combo.set_active(1)
        criterion_entry = Gtk.Entry()
        criterion_entry.connect("changed", self.on_filter_criterion_changed,
                                criterion_combo)
        box.pack_start(criterion_combo, False, False, 0)
        box.pack_start(criterion_entry, True, True, 0)
        return box

    def refresh(self):
        """reloads the entire liststore"""
        self.liststore.clear()
        for spectrum in self.s_container:
            fields = (str(spectrum["Name"]), str(spectrum["Notes"]),
                      str(spectrum["Sweeps"]), str(spectrum["DwellTime"]),
                      str(spectrum["PassEnergy"]), spectrum)
            self.liststore.append(fields)

    def refill(self, container):
        """fills in another given container into the liststore"""
        self.s_container = container
        self.refresh()

    def spectrum_filter_func(self, model, iter_, _data):
        """returns true for entries that should still show"""
        if self.current_filter is None:
            return True
        else:
            col_index = self.current_filter[0]
            search_term = self.current_filter[1]
            regex = re.compile(r".*{0}.*".format(search_term), re.IGNORECASE)
            return re.match(regex, model[iter_][col_index])

    def on_filter_criterion_changed(self, entry, combo):
        """applies new filter"""
        colname = combo.get_active_text()
        search_term = entry.get_text()
        if colname is None or len(search_term) == 0:
            self.current_filter = None
        else:
            col_index = self.used_titles.index(colname)
            self.current_filter = (col_index, search_term)
        self.filter_.refilter()

#     def build_context_menu(self):
#         """builds a context menu for clicking inside the treeview"""
#         menu = Gtk.Menu()
#         for item in ["Show all selected", "Edit"]:
#             menu_item = Gtk.MenuItem(item)
#             menu.append(menu_item)
#         menu.show_all()
#         return menu

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
            storerow = self.liststore[iter_]
            self.menu.popup(None, None, None, None, event.button, event.time)
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            storerow = self.liststore[iter_]
            self.s_container.show_only(storerow[-1])
            self.mainwindow.refresh_canvas(keepaxes=False)


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
