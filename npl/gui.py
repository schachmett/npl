"""this module manages the windows of npl"""
# pylint: disable=C0413

import os
import re

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3

from npl import __appname__, __version__, __authors__, __config__
from npl.fileio import FileParser, DBHandler, RSFHandler
from npl.drawer import Plotter
from npl.containers import Spectrum, SpectrumContainer


class Npl(Gtk.Application):
    # pylint: disable=W0221
    """ application class """
    def __init__(self):
        super().__init__(application_id="org.npl.app",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        GLib.set_application_name(__appname__)

        self.s_container = SpectrumContainer()
        self.parser = FileParser()
        self.dbhandler = DBHandler()

        self.dbfilename = None
        self.win = None

        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "cmd test", None)

    def do_activate(self):
        """ activates window? """
        self.win = MainWindow(app=self)
        self.win.show_all()

    def do_startup(self):
        """ startup stuff, for now only menu bar """
        Gtk.Application.do_startup(self)

        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.do_new)
        self.add_action(new_action)
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.do_save)
        self.add_action(save_action)
        save_as_action = Gio.SimpleAction.new("save_as", None)
        save_as_action.connect("activate", self.do_save_as)
        self.add_action(save_as_action)
        add_action = Gio.SimpleAction.new("add_spectrum", None)
        add_action.connect("activate", self.do_add_spectrum)
        self.add_action(add_action)
        remove_action = Gio.SimpleAction.new("remove_spectrum", None)
        remove_action.connect("activate", self.do_remove_spectrum)
        self.add_action(remove_action)
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.do_quit)
        self.add_action(quit_action)

        builder = Gtk.Builder.new_from_file(os.path.join(
            __config__.get("general", "basedir"), "gtk/menus.ui"))
        self.set_menubar(builder.get_object("menubar"))

    def do_command_line(self, command_line):
        """ handles command line arguments """
        options = command_line.get_options_dict()
        if options.contains("test"):
            print("Test argument received")
        self.activate()
        return 0

    def ask_for_save(self, container):
        """ opens a AskForSaveDialog and runs the appropriate methods,
        then returns True if user really wants to close current file """
        if not container:
            return True
        dialog = AskForSaveDialog(self.win)
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            dialog.destroy()
            is_saved = self.do_save()
            return is_saved
        if response == Gtk.ResponseType.NO:
            dialog.destroy()
            return True
        dialog.destroy()
        return False

    def do_new(self, *_ignore):
        """ start new project """
        really_do_it = self.ask_for_save(self.s_container)
        if really_do_it:
            self.s_container.clear()
            self.win.refresh()
            self.dbfilename = None
            __config__.set("io", "project_file", "None")

    def do_save(self, *_ignore):
        """ saves project """
        if self.dbfilename is None:
            self.do_save_as()
        else:
            self.dbhandler.change_dbfile(self.dbfilename)
            self.dbhandler.wipe_tables()
            self.dbhandler.save_container(self.s_container)
            __config__.set("io", "project_file", self.dbfilename)
            return True

    @staticmethod
    def file_chooser_filter(name, patterns):
        """ filter for file chooser dialogs """
        filter_ = Gtk.FileFilter()
        for pattern in patterns:
            filter_.add_pattern(pattern)
        filter_.set_name(name)
        return filter_

    def do_save_as(self, *_ignore):
        """ saves project in a new file to be specified """
        dialog = Gtk.FileChooserDialog("Save as...", self.win,
                                       Gtk.FileChooserAction.SAVE,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Save", Gtk.ResponseType.OK))
        dialog.set_do_overwrite_confirmation(True)
        dialog.add_filter(self.file_chooser_filter(".npl", ["*.npl"]))
        dialog.set_current_name("untitled.npl")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            if fname[-4:] != ".npl":
                fname += ".npl"
            self.dbfilename = fname
            self.do_save()
        dialog.destroy()

    def do_open_project(self, *_ignore):
        """ opens project from a file """
        really_do_it = self.ask_for_save(self.s_container)
        if not really_do_it:
            return
        dialog = Gtk.FileChooserDialog("Open...", self.win,
                                       Gtk.FileChooserAction.OPEN,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Open", Gtk.ResponseType.OK))
        dialog.add_filter(self.file_chooser_filter(".npl", ["*.npl"]))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.s_container.clear()
            fname = dialog.get_filename()
            self.dbfilename = fname
            self.dbhandler.change_dbfile(self.dbfilename)
            container = self.dbhandler.get_container()
            for spectrum in container:
                self.s_container.append(spectrum)
            __config__.set("io", "project_file", self.dbfilename)
        self.win.refresh()
        dialog.destroy()

    def open_silently(self, fname):
        """ opens a project silently, e. g. for opening the last project at
        startup """
        self.s_container.clear()
        self.dbfilename = fname
        self.dbhandler.change_dbfile(self.dbfilename)
        container = self.dbhandler.get_container()
        for spectrum in container:
            self.s_container.append(spectrum)
        __config__.set("io", "project_file", self.dbfilename)

    def do_add_spectrum(self, *_ignore):
        """ imports a spectrum file and adds it to the current container """
        dialog = Gtk.FileChooserDialog("Import data...", self.win,
                                       Gtk.FileChooserAction.OPEN,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Open", Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)
        dialog.add_filter(self.file_chooser_filter("all files",
                                                   ["*.xym", "*.txt", "*.xy"]))
        dialog.add_filter(self.file_chooser_filter(".xym", ["*.xym"]))
        dialog.add_filter(self.file_chooser_filter(".txt", ["*.txt"]))

        parseds = list()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for fname in dialog.get_filenames():
                if fname.split(".")[-1] in ["xym", "txt"]:
                    parseds.extend(self.parser.parse_spectrum_file(fname))
                elif fname.split(".")[-1] in ["xy"]:
                    print("not yet implemented")
                else:
                    print("file {} not recognized".format(fname))
            for raw_spectrum in parseds:
                spectrum = Spectrum(raw_spectrum)
                self.s_container.append(spectrum)
            self.win.refresh_treeview()
        else:
            print("nothing selected")
        dialog.destroy()

    def do_remove_spectrum(self, *_ignore):
        """ removes selected spectra """
        spectra = self.win.sview.get_selected_spectra()
        for spectrum in spectra:
            self.s_container.remove(spectrum)
        self.win.refresh()

    def do_quit(self, *_ignore):
        """ quit program """
        cfg_name = __config__.get("general", "conf_filename")
        with open(cfg_name, "w") as cfg_file:
            __config__.write(cfg_file)
        self.quit()


class MainWindow(Gtk.ApplicationWindow):
    """ main window composed mainly of treeview and mpl canvas """
    def __init__(self, app):
        self.app = app
        super().__init__(title=__appname__, application=app)
        self.set_size_request(int(__config__.get("window", "xsize")),
                              int(__config__.get("window", "ysize")))
        self.set_icon_from_file(os.path.join(
            __config__.get("general", "basedir"), "icons/logo.svg"))
        self.connect("delete-event", self.app.do_quit)

        self.s_container = self.app.s_container
        self.sview = SpectrumView(self.app)
        self.cvs = Canvas(self.app, self)
        self.toolbar = ToolBar(self.app, self)
        self.build_window()

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.do_about)
        self.add_action(about_action)
        show_selected_action = Gio.SimpleAction.new("show_selected", None)
        show_selected_action.connect("activate", self.do_show_selected)
        self.add_action(show_selected_action)
        debug_action = Gio.SimpleAction.new("debug", None)
        debug_action.connect("activate", self.do_debug)
        self.add_action(debug_action)

    def build_window(self):
        """ do gtk boxing stuff """
        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        contentpanes = Gtk.HPaned()
        contentpanes.shrink = False
        self.add(masterbox)
        masterbox.pack_start(self.toolbar, False, False, 0)
        masterbox.pack_start(contentpanes, True, True, 0)
        contentpanes.pack1(self.sview, False, False)
        contentpanes.pack2(self.cvs, True, False)

    def refresh_treeview(self):
        """ treeview reads its data again from the container """
        self.sview.refresh()

    def refresh_canvas(self, keepaxes=False):
        """ plotter refetches its info and redraws """
        self.cvs.refresh(keepaxes)

    def refresh(self):
        """ refreshes window components """
        self.refresh_treeview()
        self.refresh_canvas()

    def do_about(self, *_ignore):
        """ show about dialog """
        aboutdialog = Gtk.AboutDialog()
        aboutdialog.set_transient_for(self)
        aboutdialog.set_program_name(__appname__)
        aboutdialog.set_authors(__authors__)
        aboutdialog.set_version(__version__)
        aboutdialog.set_license_type(Gtk.License.GPL_3_0)
        aboutdialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.join(__config__.get("general", "basedir"),
                         "icons/logo.svg"),
            50, -1, True))
        aboutdialog.connect("response", self.on_close_dialog)
        aboutdialog.show()

    def do_debug(self, *_ignore):
        """ allows for testing stuff from gui """
        print(self)

    def do_show_rsf(self, *_ignore):
        """ calls the canvasbox method to show rsf values in plot """
        self.cvs.on_show_rsf()

    def do_select_energyrange(self, *_ignore):
        """ calls canvasbox method to select an energy range """
        self.cvs.on_select_energyrange()

    def do_show_selected(self, *_ignore):
        """ plots spectra that are selected in the treeview """
        self.sview.on_show_selected()

    @staticmethod
    def on_close_dialog(action, *_ignore):
        """ closes the action (e.g. dialog) """
        action.destroy()


class ToolBar(Gtk.Toolbar):
    """ main toolbar for file operations """
    def __init__(self, app, parent):
        super().__init__()
        self.app = app
        self.parent = parent
        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.toolitems = (
            ("document-new", self.app, "do_new"),
            ("document-save", self.app, "do_save"),
            ("document-save-as", self.app, "do_save_as"),
            ("document-open", self.app, "do_open_project"),
            (None, None, None),
            ("list-add", self.app, "do_add_spectrum"),
            ("list-remove", self.app, "do_remove_spectrum"),
            (None, None, None),
            (os.path.join(__config__.get("general", "basedir"),
                          "icons/elements3.png"),
             self.parent, "do_show_rsf"),
            (os.path.join(__config__.get("general", "basedir"),
                          "icons/xrangesel.png"),
             self.parent, "do_select_energyrange"))
        for icon_name, class_, callback in self.toolitems:
            if icon_name is None:
                self.insert(Gtk.SeparatorToolItem(), -1)
                continue
            tbutton = Gtk.ToolButton()
            if os.path.isfile(icon_name):
                icon = Gtk.Image.new_from_file(icon_name)
                tbutton.set_icon_widget(icon)
            else:
                tbutton.set_icon_name(icon_name)
            self.insert(tbutton, -1)
            tbutton.connect("clicked", getattr(class_, callback))


class SpectrumView(Gtk.Box):
    """ treeview containing spectrum information """
#         To do: make reorderable work (for dragging/dropping list items)
#         treeview.set_reorderable(True)
#         treeview.connect("drag_data_received", self.on_test)

    col_keys = ["Name", "Notes", "Sweeps", "DwellTime", "PassEnergy"]
    col_titles = ["Name", "Notes", "Sweeps", "Dwell [s]", "Pass [eV]"]
    maincol = col_titles.index("Notes")

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.liststore = None
        self.model = self.create_model()
        self.current_filter = None
        self.menu = self.build_context_menu()
        self.treeview = self.build_treeview()

        scrollable = Gtk.ScrolledWindow()
        scrollable.set_property("min-content-width", 300)
        scrollable.add(self.treeview)
        filterbar = self.build_filterbar()
        self.pack_start(scrollable, True, True, 0)
        self.pack_start(filterbar, False, False, 0)

    def create_model(self):
        """ create liststore and load it with the given spectrum keys as well
        as the spectrum itself, then wrap a filtermodel and a modelsort
        around it """
        number_of_cols = len(self.col_keys)
        types = [str, ] * number_of_cols + [object]
        self.liststore = Gtk.ListStore(*types)
        for spectrum in self.app.s_container:
            row = [str(spectrum[key]) for key in self.col_keys] + [spectrum]
            self.liststore.append(row)
        self.filter_model = self.liststore.filter_new()
        self.filter_model.set_visible_func(self.spectrum_filter_func)
        sorted_model = Gtk.TreeModelSort(self.filter_model)
        return sorted_model

    def build_treeview(self):
        """ builds treeview with columns and fills in the model """
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
        """ renders the cell from a spectrum object """
        col_key = self.col_keys[self.col_titles.index(col_title)]
        value = treemodel[iter_][-1][col_key]
        renderer.set_property("text", str(value))

    def refresh(self, *_ignore):
        """ makes new treemodel from the container and gives it to the
        treeview """
        self.model = self.create_model()
        self.treeview.set_model(self.model)

    def build_filterbar(self):
        """ builds the widget on the bottom for filtering the entries """
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

    def on_filter_criterion_changed(self, entry, combo):
        """ applies new filter """
        col_title = combo.get_active_text()
        search_term = entry.get_text()
        if col_title is None or not search_term:
            self.current_filter = None
        else:
            col_index = self.col_titles.index(col_title)
            self.current_filter = (col_index, search_term)
        self.filter_model.refilter()

    def spectrum_filter_func(self, model, iter_, _data):
        """ returns true for entries that should still show """
        if self.current_filter is None:
            return True
        col_index = self.current_filter[0]
        search_term = self.current_filter[1]
        regex = re.compile(r".*{0}.*".format(search_term), re.IGNORECASE)
        return re.match(regex, model[iter_][col_index])

    def on_row_clicked(self, treeview, event):
        """ click events inside treeview:
        right click: context menu for amending spectrum / showing selected etc
        double click: plot single spectrum """
        posx = int(event.x)
        posy = int(event.y)
        pathinfo = treeview.get_path_at_pos(posx, posy)
        if pathinfo is not None:
            path, _col, _cellx, _celly = pathinfo
        else:
            return
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup(None, None, None, None, event.button, event.time)
            return path in self.selection.get_selected_rows()[1]
        # pylint: disable=W0212
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.on_show_selected()
            return True

    def build_context_menu(self):
        """ builds the right click menu """
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
        """ gives the selected spectra to the plotter """
        spectra = self.get_selected_spectra()
        self.app.s_container.show_only(spectra)
        self.app.win.refresh_canvas(keepaxes=False)

    def on_edit_spectrum(self, _action):
        """ edits fields in the spectrum thorugh a EditSpectrumDialog and
        refreshes """
        model, pathlist = self.selection.get_selected_rows()
        spectra = []
        for path in pathlist:
            iter_ = model.get_iter(path)
            spectra.append(model[iter_][-1])
        dialog = EditSpectrumDialog(self.app.win, spectra)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            user_input = dialog.get_user_input()
            for spectrum in spectra:
                for key, value in user_input:
                    if dialog.excluding_key not in value and value != "":
                        spectrum[key] = value
        self.refresh()
        dialog.destroy()

    def get_selected_spectra(self, *_ignore):
        """ gives the selected spectra to the plotter """
        model, pathlist = self.selection.get_selected_rows()
        spectra = []
        for path in pathlist:
            iter_ = model.get_iter(path)
            spectra.append(model[iter_][-1])
        return spectra


class EditSpectrumDialog(Gtk.Dialog):
    """ shows a dialog with entries to change metadata, needs a parent and
    a list of spectra """
    excluding_key = " (multiple)"
    spectrum_keys = SpectrumView.col_keys
    spectrum_titles = SpectrumView.col_titles

    def __init__(self, parent, spectra):
        super().__init__("Settings", parent, 0,
                         ("_Cancel", Gtk.ResponseType.CANCEL,
                          "_OK", Gtk.ResponseType.OK))
        self.set_size_request(500, -1)
        okbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.OK)
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
        fnames = "\n".join(list(
            str(spectrum["Filename"]) for spectrum in self.spectra))
        fnames_label = Gtk.Label(label=fnames)
        fnamebox.pack_start(fname_title_label, False, False, 10)
        fnamebox.pack_start(fnames_label, True, True, 10)
        self.box.pack_start(fnamebox, False, False, 5)
        for key in SpectrumView.col_keys:
            self.box.pack_start(self.generate_entry(key), False, False, 2)
        self.show_all()

    def generate_entry(self, key):
        """ makes an entry for the dialog """
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
        """ gives the values that the user put in as a list of tuples:
        [(key, new_value), (key2, new_value2), ...] """
        user_input = list()
        for i, key in enumerate(self.spectrum_keys):
            user_input.append((key, self.entries[i].get_text()))
        return user_input


class AskForSaveDialog(Gtk.Dialog):
    """ asks if you are sure to quit/make new file without saving """
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


class SelectElementsDialog(Gtk.Dialog):
    """ lets the user select elements and a source for rsf plotting """
    sources = ["Al", "Mg"]

    def __init__(self, parent, default_source, default_elements):
        super().__init__("Element Library", parent, 0,
                         ("_Cancel", Gtk.ResponseType.CANCEL,
                          "_OK", Gtk.ResponseType.OK))
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

        rowbox1 = Gtk.Box()
        rowbox1.pack_start(Gtk.Label("Source", width_chars=15),
                           False, False, 10)
        rowbox1.pack_start(self.source_combo, True, True, 10)
        rowbox2 = Gtk.Box()
        rowbox2.pack_start(Gtk.Label("Elements", width_chars=15),
                           False, False, 10)
        rowbox2.pack_start(self.elements_entry, True, True, 10)
        self.box.pack_start(rowbox1, False, False, 2)
        self.box.pack_start(rowbox2, False, False, 2)
        self.show_all()

    def get_user_input(self):
        """ gives elements and Sources selected """
        source = self.source_combo.get_active_text()
        elementstring = self.elements_entry.get_text()
        elements = re.findall(r"[\w]+", elementstring)
        elements = [element.title() for element in elements]
        return [source, elements]


class Canvas(Gtk.Box):
    """ plotting area box """
    def __init__(self, app, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.parent = parent
        self.plotter = Plotter()

        self.pack_start(self.plotter.get_canvas(), True, True, 0)
        navbar = MPLNavBar(self.plotter, self.parent)
        self.pack_start(navbar, False, False, 0)

        self.rsfhandler = RSFHandler(
            os.path.join(__config__.get("general", "basedir"), "rsf.db"))

        self.refresh()

    def refresh(self, keepaxes=False):
        """ redraws canvas """
        self.plotter.plot(self.app.s_container, keepaxes)

    def on_show_rsf(self):
        """ makes a SelectElementsDialog and hands the user input to the
        plotter """
        dialog = SelectElementsDialog(self.app.win, self.rsfhandler.source,
                                      self.rsfhandler.elements)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.rsfhandler.reset()
            source, elements = dialog.get_user_input()
            rsf_dicts = []
            for element in elements:
                rsf_dicts.extend(self.rsfhandler.get_element(element, source))
            self.plotter.change_rsf(source, rsf_dicts)
        dialog.destroy()

    def on_select_energyrange(self):
        """ calls the plotter energy range selector method """
        self.plotter.get_xrange()


class MPLNavBar(NavigationToolbar2GTK3):
    """ navbar for the canvas """
    def __init__(self, plotter, parent):
        self.plotter = plotter
        self.parent = parent
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
        super().__init__(self.plotter.get_canvas(), self.parent)

    def fit_view(self, _event):
        """ centers the view to plotted graphs, mapped to home button """
        if self._views.empty():
            self.push_current()
        self.plotter.recenter_view()
        self.parent.refresh_canvas()
        self.push_current()
        self._update_view()
