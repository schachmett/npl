#!/usr/bin/python3.5
"""this module manages the windows of npl"""

import os
import json
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
from matplotlib.widgets import SpanSelector
import npl_plotter
import re

WIN_XSIZE = 1200
WIN_YSIZE = 700
BASEDIR = "/home/simon/npl/"
SETTINGS_FOLDER = os.path.join(BASEDIR, ".npl/")
SETTINGS_FILE = SETTINGS_FOLDER + "/settings.json"
SETTINGS = {}


def manage_globals():
    """manages the module constants"""
    global SETTINGS

    if not os.path.isdir(SETTINGS_FOLDER):
        os.mkdir(SETTINGS_FOLDER)
    if not os.path.isfile(SETTINGS_FILE):
        SETTINGS = {"project_file": None}
        with open(SETTINGS_FILE, 'w') as settingsfile:
            json.dump(SETTINGS, settingsfile, indent=4)
    else:
        with open(SETTINGS_FILE, 'r') as settingsfile:
            SETTINGS = json.load(settingsfile)
        if not os.path.isfile(str(SETTINGS["project_file"])):
            SETTINGS["project_file"] = None


def main():
    """creates the main window and runs it"""
    manage_globals()
    mainwindow = MainWindow()
    mainwindow.connect("delete-event", program_exit)
    mainwindow.set_size_request(WIN_XSIZE, WIN_YSIZE)
    mainwindow.set_icon_from_file(os.path.join(BASEDIR, "icons/logo.svg"))
    mainwindow.show_all()
    Gtk.main()


def program_exit(widget, event):
    """does work when exiting program"""
    with open(SETTINGS_FILE, 'w') as settingsfile:
        json.dump(SETTINGS, settingsfile, indent=4)
    Gtk.main_quit()


class MainWindow(Gtk.Window):
    """main window, containing the toolbar and 2 hpanes with the treeview and
    the canvas"""
    def __init__(self):
        super().__init__(title="XPSlotty")
        self.slist = SpectrumList(self)
        self.database = npl_plotter.Database(self.slist.liststore)
        if SETTINGS["project_file"] is not None:
            if os.path.isfile(SETTINGS["project_file"]):
                self.database.load(SETTINGS["project_file"])
        self.rsflib = npl_plotter.RSFlib()
        
        self.plotter = npl_plotter.Plotter(self.database, self.rsflib)
        toolbar = ToolBar(self, self.database)
        mpltoolbar = NavBar(self.plotter.canvas, self, self.plotter)
        anbar = AnalyzeBar(self.plotter.canvas, self, self.plotter)
        
        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        contentpanes = Gtk.HPaned()
        contentpanes.shrink = False
        canvasbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(masterbox)
        masterbox.pack_start(toolbar, False, False, 0)
        masterbox.pack_start(contentpanes, True, True, 0)
        canvasbox.pack_start(anbar, False, False, 0)
        canvasbox.pack_start(self.plotter.canvas, True, True, 0)
        canvasbox.pack_start(mpltoolbar, False, False, 0)
        contentpanes.pack1(self.slist, False, False)
        contentpanes.pack2(canvasbox, True, False)
        self.plotter.refresh()


class SpectrumList(Gtk.Box):
    """treeview in a box, shows loaded spectra"""
    
    def __init__(self, mainwindow):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.mainwindow = mainwindow
        self.cols = {"Plot": None, "Name": None, "Notes": None, "E_s [eV]": None,
                     "E_e [eV]": None, "Sweeps": None, "Dwell [s]": None}


        self.liststore = Gtk.ListStore(bool, str, str, str, str, str, str, object)
        self.current_filter = None
        self.filter_ = self.liststore.filter_new()
        self.filter_.set_visible_func(self.spectrum_filter_func)
        self.treeview = Gtk.TreeView.new_with_model(self.filter_)

        self.treeview.connect("button-press-event", self.on_row_clicked)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.set_rules_hint(True)
        # reorder and sort columns

        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_spectrum_toggled)
        column = Gtk.TreeViewColumn("Plot", renderer, active=0)
        self.treeview.append_column(column)
        self.cols["Plot"] = 0
        
        renderer = Gtk.CellRendererText(editable=True)
        renderer.connect("edited", self.on_namecol_edited)
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        column.set_resizable(True)
        self.treeview.append_column(column)
        self.cols["Name"] = 1
        
        for i, column_title in enumerate(["Notes", "E_s [eV]", "E_e [eV]", "Sweeps", "Dwell [s]"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i+2)
            column.set_resizable(True)
            self.treeview.append_column(column)
        self.cols["Notes"] = 2
        self.cols["E_s [eV]"] = 3
        self.cols["E_e [eV]"] = 4
        self.cols["Sweeps"] = 5
        self.cols["Dwell [s]"] = 6

        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_property("min-content-width", 300)
        self.scrollable_treelist.add(self.treeview)
        #~ self.buttonbox = self.create_filtering_buttons("None", "1", "2",
                                                       #~ "4", "6", "8")
        self.filterbar = self.create_filterbar()
        self.pack_start(self.scrollable_treelist, True, True, 0)
        self.pack_start(self.filterbar, False, False, 0)

    def spectrum_filter_func(self, model, iter_, data):
        """function for filtering treeview"""
        if self.current_filter is None:
            return True
        else:
            column = self.current_filter[0]
            regex = re.compile("".join([".*", self.current_filter[1], ".*"]))
            return re.match(regex, model[iter_][column])

    def create_filterbar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_size_request(-1, 30)
        
        criterion_combo = Gtk.ComboBoxText()
        criterion_combo.set_entry_text_column(0)
        for colname in sorted(self.cols, key=self.cols.get)[1:]:
            criterion_combo.append_text(colname)
        criterion_combo.set_active(1)

        criterion_entry = Gtk.Entry()
        criterion_ok = Gtk.Button(label=None, image=Gtk.Image(stock=Gtk.STOCK_FIND))
        criterion_ok.connect("clicked", self.on_filter_criterion_changed, criterion_combo, criterion_entry)
        criterion_cancel = Gtk.Button(label=None, image=Gtk.Image(stock=Gtk.STOCK_CANCEL))
        criterion_cancel.connect("clicked", self.on_filter_criterion_deleted)
        
        box.pack_start(criterion_combo, False, False, 0)
        box.pack_start(criterion_entry, False, False, 0)
        box.pack_start(criterion_ok, False, False, 0)
        box.pack_start(criterion_cancel, False, False, 0)
        return box

    def on_filter_criterion_changed(self, widget, combo, entry):
        colname = combo.get_active_text()
        if colname is None:
            self.current_filter == None
            print("no search criterion selected")
        else:
            column = self.cols[colname]
            sterm = entry.get_text()
            self.current_filter = (column, sterm)
            print("search column {} for: {}".format(colname, sterm))
        self.filter_.refilter()

    def on_filter_criterion_deleted(self, widget):
        self.current_filter = None
        self.filter_.refilter()

    def on_spectrum_toggled(self, renderer, path):
        """turn off visibility of spectra"""
        if path is not None:
            iter_ = self.liststore.get_iter(path)
            listrow = self.liststore[iter_]
            listrow[self.cols["Plot"]] = not listrow[self.cols["Plot"]]
            listrow[-1]["Visible"] = not listrow[-1]["Visible"]
            self.mainwindow.plotter.ax.cla()
            self.mainwindow.plotter.refresh(keepaxes=True)

    def on_row_clicked(self, treeview, event):
        try:
            path, colum, cellx, celly = treeview.get_path_at_pos(int(event.x),
                                                                 int(event.y))
        except TypeError:
            # print("clicked beside row")
            return
        iter_ = self.liststore.get_iter(path)
        if event.button == 3:
            storerow = self.liststore[iter_]
            settingstrings = ["Name", "Sweeps", "Dwelltime", "Notes"]
            colnumbers = [self.cols["Name"], self.cols["Sweeps"],
                          self.cols["Dwell [s]"], self.cols["Notes"]]
            settings = storerow[-1].values_by_keylist(settingstrings)
            dialog = EnterStringsDialog(self.mainwindow, settingstrings, settings)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                outdict = dialog.output()
                for field, value in outdict.items():
                    storerow[-1][field] = value
                for colnr, field in zip(colnumbers, settingstrings):
                    if colnr is not None:
                        type_ = type(storerow[colnr])
                        storerow[colnr] = type_(outdict[field])
            dialog.destroy()

    def on_namecol_edited(self, renderer, path, newtext):
        """edits column and stores info in respective Spectrum"""
        if path is not None:
            iter_ = self.liststore.get_iter(path)
            self.liststore[iter_][SpectrumList.NAMECOL] = newtext
            self.liststore[iter_][-1]["Name"] = newtexts


class EnterStringsDialog(Gtk.Dialog):
    def __init__(self, parent, fields, defaults=None):
        super().__init__("Settings", parent, 0,
                         (Gtk.STOCK_CANCEL,
                          Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_OK,
                          Gtk.ResponseType.OK))

        box = self.get_content_area()

        self.entries = []
        
        for i, field in enumerate(fields):
            row = Gtk.Box()
            label = Gtk.Label(label=field)
            entry = Gtk.Entry()
            if defaults is not None:
                entry.set_text(str(defaults[i]))
            self.entries.append((field, entry))
            row.pack_start(label, True, True, 10)
            row.pack_start(entry, False, True, 0)
            box.pack_start(row, False, False, 0)
        self.show_all()

    def output(self):
        outdict = {}
        for field, entry in self.entries:
            outdict[field] = entry.get_text()
        return outdict


class ToolBar(Gtk.Toolbar):
    """toolbar at the top for adding/removing spectra and saving/opening
    projects"""
    def __init__(self, mainwindow, database):
        super().__init__()
        self.mainwindow = mainwindow
        self.database = database
        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.toolitems = (
                ("list-add", "add_spectrum"),
                ("list-remove", "remove_spectrum"),
                (None, None),
                ("document-save", "save_project"),
                ("document-save-as", "save_project_as"),
                ("document-open", "open_project")
            )
        for icon_name, callback in self.toolitems:
            if icon_name is None:
                self.insert(Gtk.SeparatorToolItem(), -1)
                continue
            tbutton = Gtk.ToolButton()
            tbutton.set_icon_name(icon_name)
            self.insert(tbutton, -1)
            tbutton.connect("clicked", getattr(self, callback))

    def add_spectrum(self, caller):
        """add spectrum to database"""
        dialog = Gtk.FileChooserDialog("Import data...", self.mainwindow,
                                       Gtk.FileChooserAction.OPEN,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN,
                                        Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)
        dialog.add_filter(self.file_chooser_filter("all files", "*.xym",
                                                   "*.txt", "*.xy"))
        dialog.add_filter(self.file_chooser_filter(".xym", "*.xym"))
        dialog.add_filter(self.file_chooser_filter(".txt", "*.txt"))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for fname in dialog.get_filenames():
                if fname.split(".")[-1] == "xym":
                    self.database.add(fname)
                elif fname.split(".")[-1] == "txt":
                    split_fnamelist = npl_plotter.unpack_eistxt(fname)
                    for split_fname in split_fnamelist:
                        self.database.add(split_fname)
                elif fname.split(".")[-1] == "xy":
                    print("not yet implemented")
                else:
                    print("file " + fname + " not recognised")
        else:
            print("nothing selected")

        self.mainwindow.plotter.refresh(keepaxes=True)
        dialog.destroy()

    def remove_spectrum(self, caller):
        """remove spectrum from database"""
        treeview = self.mainwindow.slist.treeview
        select = treeview.get_selection()
        model, pathlist = select.get_selected_rows()
        for path in pathlist[::-1]:     # go backwards, so the paths stay valid
            treeiter = model.get_iter(path)
            self.database.remove(model[treeiter][-1])
        self.mainwindow.plotter.refresh(keepaxes=True)

    def save_project_as(self, *caller):
        """save project under new file name"""
        dialog = Gtk.FileChooserDialog("Save as...", self.mainwindow,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE,
                                        Gtk.ResponseType.OK))
        dialog.set_do_overwrite_confirmation(True)
        dialog.add_filter(self.file_chooser_filter(".h5", "*.h5"))
        dialog.set_current_name("untitled.h5")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            if fname[-3:] != ".h5":
                fname += ".h5"
            self.database.dump(fname)
            print("saved project as " + fname)
            SETTINGS["project_file"] = fname
        else:
            print("project save aborted")
        dialog.destroy()

    def save_project(self, caller):
        """save project, keeping last filename"""
        fname = SETTINGS["project_file"]
        if not os.path.isfile(str(fname)):
            self.save_project_as()
        else:
            self.database.dump(fname)
            print("saved project " + fname)

    def open_project(self, caller):
        """open project from file"""
        dialog = Gtk.FileChooserDialog("Open project...", self.mainwindow,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_OPEN,
                                        Gtk.ResponseType.OK))
        dialog.add_filter(self.file_chooser_filter(".h5", "*.h5"))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            print("loaded project " + fname)
            self.database.load(fname)
            SETTINGS["project_file"] = fname
            self.mainwindow.plotter.refresh()
        else:
            print("project load aborted")
        dialog.destroy()

    def file_chooser_filter(self, name, *patterns):
        filter_ = Gtk.FileFilter()
        for pattern in patterns:
            filter_.add_pattern(pattern)
        filter_.set_name(name)
        return filter_


class NavBar(NavigationToolbar2GTK3):
    def __init__(self, canvas, window, plotter):
        self.plotter = plotter
        self.toolitems = (
                ('Fullscreen', 'Fit view to data', 'home', 'fit_view'),
                ('Back', 'Back to  previous view', 'back', 'back'),
                ('Forward', 'Forward to next view', 'forward', 'forward'),
                (None, None, None, None),
                ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
                ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
                (None, None, None, None),
                ('Save', 'Save the figure', 'filesave', 'save_figure'),
            )
        super().__init__(canvas, window)

    def fit_view(self, event):
        if self._views.empty():
            self.push_current()
        self.plotter.fit_axranges()
        self.plotter.refresh()
        self.push_current()
        self._update_view()

class AnalyzeBar(NavigationToolbar2GTK3):
    def __init__(self, canvas, window, plotter):
        self.mainwindow = window
        self.plotter = plotter
        self.toolitems = (
                ('Elements', 'Select elements', os.path.join(BASEDIR, "icons/elements"), "select_element"),
                (None, None, None, None),
                ('Select', 'Select span', os.path.join(BASEDIR, "icons/span"), 'select_span'),
                ('Shirley', 'Subtract shirley background', os.path.join(BASEDIR, "icons/shirley"), 'do_shirley')
            )
        super().__init__(canvas, window)

    def select_span(self, event):
        pass

    def do_shirley(self, event):
        pass

    def select_element(self, event):
        dialog = EnterStringsDialog(self.mainwindow, ["Elements", "Sources"],
                                    [self.mainwindow.rsflib.give_selected(),
                                     self.mainwindow.rsflib.sources[0]])
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            sourcestring = dialog.output()["Sources"]
            self.mainwindow.rsflib.set_source(sourcestring)
            
            elementstring = dialog.output()["Elements"]
            elements = re.findall(r"[\w]+", elementstring)
            self.mainwindow.rsflib.flush()
            for element in elements:
                self.mainwindow.rsflib.select(element)
            self.plotter.refresh()
        dialog.destroy()


if __name__ == '__main__':
    main()
