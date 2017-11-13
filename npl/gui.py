"""Main GUI module, manages the main window and the application class where
all user accessible actions are defined."""
# pylint: disable=wrong-import-position

import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

from npl import __appname__, __version__, __authors__, __config__
from npl.fileio import FileParser, DBHandler
from npl.containers import Spectrum, SpectrumContainer
from npl.gui_treeview import (SpectrumView, TreeViewFilterBar,
                              SpectrumContextMenu)
from npl.gui_plotter import CanvasBox, MPLNavBar


class Npl(Gtk.Application):
    # pylint: disable=arguments-differ
    """Application class, this has all the action(s)."""
    def __init__(self):
        app_id = "org.{}.app".format(__appname__.lower())
        super().__init__(application_id=app_id,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        GLib.set_application_name(__appname__)

        self.s_container = SpectrumContainer()
        self.parser = FileParser()
        self.dbhandler = DBHandler()

        self.project_fname = None
        self.win = None

        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "cmd test", None)

    def do_activate(self):
        """Creates MainWindow."""
        self.win = MainWindow(app=self)
        if __config__.get("io", "project_file") != "None":
            try:
                self.open_silently(__config__.get("io", "project_file"))
            except FileNotFoundError:
                print("file '{}' not found"
                      "".format(__config__.get("io", "project_file")))
                __config__.set("io", "project_file", "None")
        self.win.show_all()

    def do_startup(self):
        """Adds the actions and the menubar."""
        Gtk.Application.do_startup(self)

        actions = (("new", self.do_new),
                   ("save", self.do_save),
                   ("save_as", self.do_save_as),
                   ("open", self.do_open_project),
                   ("add_spectrum", self.do_add_spectrum),
                   ("remove_spectrum", self.do_remove_spectrum),
                   ("edit_spectrum", self.do_edit_spectrum),
                   ("quit", self.do_quit))
        for name, callback in actions:
            simple = Gio.SimpleAction.new(name, None)
            simple.connect("activate", callback)
            self.add_action(simple)
        builder = Gtk.Builder.new_from_file(os.path.join(
            __config__.get("general", "basedir"),
            "gtk/menus.ui"))
        self.set_menubar(builder.get_object("menubar"))

    def do_command_line(self, command_line):
        """Handles command line arguments"""
        options = command_line.get_options_dict()
        if options.contains("test"):
            print("Test argument received")
        self.activate()
        return 0

    def ask_for_save(self):
        """Opens a AskForSaveDialog and runs the appropriate methods,
        then returns True if user really wants to close current file."""
        if not self.s_container:
            return True
        if not self.s_container.altered:
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
        """Start new project."""
        really_do_it = self.ask_for_save()
        if really_do_it:
            self.win.sview.model.clear()
            self.s_container.clear()
            self.s_container.altered = False
            self.win.refresh_canvas()
            self.project_fname = None
            __config__.set("io", "project_file", "None")

    def do_save(self, *_ignore):
        """Saves project, calls do_save_as if it does not already have a
        file. Returns True if successful."""
        if self.project_fname is None:
            self.do_save_as()
        else:
            self.dbhandler.save(self.s_container, self.project_fname)
            __config__.set("io", "project_file", self.project_fname)
            self.s_container.altered = False
            return True

    def do_save_as(self, *_ignore):
        """Saves project in a new file pointed out by the user."""
        dialog = Gtk.FileChooserDialog("Save as...", self.win,
                                       Gtk.FileChooserAction.SAVE,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Save", Gtk.ResponseType.OK))
        dialog.set_do_overwrite_confirmation(True)
        dialog.add_filter(SimpleFileFilter(".npl", ["*.npl"]))
        dialog.set_current_name("untitled.npl")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            if fname[-4:] != ".npl":
                fname += ".npl"
            self.project_fname = fname
            self.do_save()
        dialog.destroy()

    def do_open_project(self, *_ignore):
        """Opens project from a file pointed out by the user, calls
        self.open_silently for the actual action."""
        really_do_it = self.ask_for_save()
        if not really_do_it:
            return
        dialog = Gtk.FileChooserDialog("Open...", self.win,
                                       Gtk.FileChooserAction.OPEN,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Open", Gtk.ResponseType.OK))
        dialog.add_filter(SimpleFileFilter(".npl", ["*.npl"]))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fname = dialog.get_filename()
            self.open_silently(fname)
        dialog.destroy()

    def open_silently(self, fname):
        """Opens a project file."""
        self.s_container.clear()
        self.project_fname = fname
        container = self.dbhandler.load(self.project_fname)
        for spectrum in container:
            self.s_container.append(spectrum)
        self.s_container.altered = False
        __config__.set("io", "project_file", self.project_fname)
        self.win.refresh_canvas()

    def do_add_spectrum(self, *_ignore):
        """Imports a spectrum file and adds it to the current container."""
        dialog = Gtk.FileChooserDialog("Import data...", self.win,
                                       Gtk.FileChooserAction.OPEN,
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_Open", Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)
        dialog.add_filter(SimpleFileFilter("all files",
                                           ["*.xym", "*.txt", "*.xy"]))
        dialog.add_filter(SimpleFileFilter(".xym", ["*.xym"]))
        dialog.add_filter(SimpleFileFilter(".txt", ["*.txt"]))

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
            self.s_container.altered = True
        else:
            print("nothing selected")
        dialog.destroy()

    def do_remove_spectrum(self, *_ignore):
        """Removes selected spectra from the container."""
        spectra = self.win.get_selected_spectra()
        for spectrum in spectra:
            self.s_container.remove(spectrum)
        self.s_container.altered = True
        self.win.refresh_canvas()

    def do_edit_spectrum(self, *_ignore):
        """Edits spectrum spectrum."""
        spectra = self.win.get_selected_spectra()
        if not spectra:
            return
        dialog = EditSpectrumDialog(self.win, spectra)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.s_container.altered = dialog.change_values()
        dialog.destroy()

    def do_quit(self, *_ignore):
        """Quit program, write to config file."""
        cfg_name = __config__.get("general", "conf_filename")
        with open(cfg_name, "w") as cfg_file:
            __config__.write(cfg_file)
        self.quit()


class MainWindow(Gtk.ApplicationWindow):
    """ main window composed mainly of treeview and mpl canvas """
    def __init__(self, app):
        self.app = app
        super().__init__(title=__appname__, application=app)
        self.connect("delete-event", self.app.do_quit)

        xsize = int(__config__.get("window", "xsize"))
        ysize = int(__config__.get("window", "ysize"))
        basedir = __config__.get("general", "basedir")
        self.set_size_request(xsize, ysize)
        self.set_icon_from_file(os.path.join(basedir, "icons/logo.svg"))
        actions = (("about", self, "do_about"),
                   ("show_selected", self, "do_show_selected"),
                   ("debug", self, "do_debug"))
        for (name, class_, callback) in actions:
            simple = Gio.SimpleAction.new(name, None)
            simple.connect("activate", getattr(class_, callback))
            self.add_action(simple)

        self.toolbar = ToolBar(self.app, self)

        self.canvasbox = CanvasBox(self.app, self)
        self.mpl_navbar = MPLNavBar(self.canvasbox.figure, self)


        context_actions = [("Show selected", self, "do_show_selected"),
                           ("Edit spectrum", self.app, "do_edit_spectrum"),
                           ("Show rsf", self.canvasbox, "on_show_rsf"),
                           ("debug", self, "do_debug")]
        self.sview = SpectrumView(self.app.s_container)
        self.sview.menu = SpectrumContextMenu(self.sview, context_actions)
        self.sview.menu.set_doubleclick_action(*context_actions[0])
        self.filterbar = TreeViewFilterBar(self.sview, "Notes")

        self.build_window()

    def build_window(self):
        """Pack the widgets into boxes."""
        sviewbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrollable = Gtk.ScrolledWindow()
        scrollable.set_property("min-content-width", 300)
        scrollable.add(self.sview)
        sviewbox.pack_start(scrollable, True, True, 0)
        sviewbox.pack_start(self.filterbar, False, False, 0)

        contentpanes = Gtk.HPaned()
        contentpanes.shrink = False
        contentpanes.pack1(sviewbox, False, False)
        contentpanes.pack2(self.canvasbox, True, False)

        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        masterbox.pack_start(self.toolbar, False, False, 0)
        masterbox.pack_start(contentpanes, True, True, 0)
        self.add(masterbox)

    def refresh_canvas(self, keepaxes=False):
        """Figure refetches its info and redraws."""
        self.canvasbox.refresh(keepaxes)

    def do_about(self, *_args, **kwargs):
        """Show "About" dialog."""
        if "logo_path" in kwargs:
            logo_path = kwargs["logo_path"]
        else:
            logo_path = os.path.join(__config__.get("general", "basedir"),
                                     "icons/logo.svg")
        logo = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 50, -1, True)
        aboutdialog = Gtk.AboutDialog()
        aboutdialog.set_transient_for(self)
        aboutdialog.set_program_name(__appname__)
        aboutdialog.set_authors(__authors__)
        aboutdialog.set_version(__version__)
        aboutdialog.set_license_type(Gtk.License.GPL_3_0)
        aboutdialog.set_logo(logo)

        def destroy(*_args):
            """Destroys the about dialog, function used for callback."""
            aboutdialog.destroy()
        aboutdialog.connect("response", destroy)
        aboutdialog.show()

    def do_debug(self, *_ignore):
        """Allows for testing stuff from GUI."""
        # self.app.s_container[0].set("Notes", "nothing")
        self.refresh_canvas()
        # self.sview.filter_by("Notes", "detail")
        # print(value)

    def do_show_rsf(self, *_ignore):
        """ calls the canvasbox method to show rsf values in plot """
        # self.cvs.on_show_rsf()
        pass

    def do_select_energyrange(self, *_ignore):
        """ calls canvasbox method to select an energy range """
        # self.cvs.on_select_energyrange()
        pass

    def do_show_selected(self, *_ignore):
        """Plots spectra that are selected in the SpectrumView."""
        spectra = self.get_selected_spectra()
        self.app.s_container.show_only(spectra)
        self.refresh_canvas(keepaxes=False)

    def get_selected_spectra(self, *_ignore):
        """Returns the spectra currently selected in the SpectrumView."""
        return self.sview.get_selected_spectra()


class ToolBar(Gtk.Toolbar):
    """Main toolbar for file operations."""
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


class EditSpectrumDialog(Gtk.Dialog):
    """Shows a dialog with entries to change metadata, needs a parent and
    a list of spectra."""
    excluding_key = " (multiple)"

    def __init__(self, parent, spectra, keys=None):
        super().__init__("Settings", parent, 0,
                         ("_Cancel", Gtk.ResponseType.CANCEL,
                          "_OK", Gtk.ResponseType.OK))
        if not spectra:
            self.response(Gtk.ResponseType.CANCEL)
            return
        self.set_size_request(300, -1)
        okbutton = self.get_widget_for_response(
            response_id=Gtk.ResponseType.OK)
        okbutton.set_can_default(True)
        okbutton.grab_default()

        if keys is not None:
            self.titles = [(key, spectra[0].titles[key]) for key in keys]
        else:
            self.titles = [(key, title)
                           for key, title in spectra[0].titles.items()]

        self.spectra = spectra
        self.entries = list()
        self.multiple = len(spectra) != 1
        self.box = self.get_content_area()

        self.build_window()
        self.show_all()

    def build_window(self):
        """Creates the labels and entries and orders them."""
        fnamebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        fname_title_label = Gtk.Label(label="Filename(s):", width_chars=15)
        fnames = ""
        for spectrum in self.spectra:
            try:
                fnames += spectrum["Filename"] + "\n"
            except KeyError:
                fnames += "unknown file name\n"
        fnames = fnames.strip()
        fnames_label = Gtk.Label(label=fnames)
        fnamebox.pack_start(fname_title_label, False, False, 10)
        fnamebox.pack_start(fnames_label, True, True, 10)
        self.box.pack_start(fnamebox, False, False, 5)

        for (key, title) in self.titles:
            if key != "Filename":
                self.box.pack_start(self.generate_entry(key, title),
                                    False, False, 2)

    def generate_entry(self, key, title):
        """Makes an entry with a specific title for a spectrum key."""
        if not self.multiple:
            value = str(self.spectra[0].get(key))
        else:
            values = []
            for spectrum in self.spectra:
                values.append(str(spectrum.get(key)))
            value = " | ".join(set(values)) + self.excluding_key

        label = Gtk.Label(label=title, width_chars=15)
        entry = Gtk.Entry(text=value)
        entry.set_activates_default(True)
        self.entries.append(entry)

        rowbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rowbox.pack_start(label, False, False, 10)
        rowbox.pack_start(entry, True, True, 10)
        return rowbox

    def change_values(self):
        """Actually changes the values of the spectra."""
        altered = False
        for spectrum in self.spectra:
            for i, (key, _title) in enumerate(self.titles):
                new_value = self.entries[i].get_text()
                if self.excluding_key not in new_value:
                    spectrum.set(key, new_value)
                    altered = True
        return altered


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
