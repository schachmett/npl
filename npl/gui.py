"""Main GUI module, manages the main window and the application class where
all user accessible actions are defined."""
# pylint: disable=wrong-import-position

import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, GdkPixbuf
import numpy as np

from npl import __appname__, __version__, __authors__, __config__
from npl.fileio import FileParser, DBHandler
from npl.containers import SpectrumContainer
from npl.gui_treeview import (
    ContainerView, TreeViewFilterBar, ContainerContextMenu, SpectrumSettings)
from npl.gui_regions import RegionManager
from npl.gui_plotter import CanvasBox
from npl.gui_dialogs import (
    EditSpectrumDialog, AskForSaveDialog, SimpleFileFilter)


class Npl(Gtk.Application):
    # pylint: disable=arguments-differ
    # TODO: cview does not load attributes correctly when importing
    """Application class, this has all the action(s)."""
    def __init__(self):
        app_id = "org.{}.app".format(__appname__.lower())
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        GLib.set_application_name(__appname__)

        self.s_container = SpectrumContainer()
        self.parser = FileParser()
        self.dbhandler = DBHandler()

        self.project_fname = None
        self.win = None

        self.add_main_option(
            "test",
            ord("t"),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE, "cmd test", None)

    def do_activate(self):
        """Creates MainWindow."""
        self.win = MainWindow(app=self)
        if __config__.get("io", "project_file") != "None":
            try:
                self.open_silently(__config__.get("io", "project_file"))
            except FileNotFoundError:
                print(
                    "file '{}' not found".format(
                        __config__.get("io", "project_file")))
                __config__.set("io", "project_file", "None")
        self.win.show_all()

    def do_startup(self):
        """Adds the actions and the menubar."""
        Gtk.Application.do_startup(self)

        actions = (
            ("new", self.do_new),
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
            self.s_container.clear()
            self.s_container.altered = False
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
        dialog = Gtk.FileChooserDialog(
            "Save as...",
            self.win,
            Gtk.FileChooserAction.SAVE,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_Save", Gtk.ResponseType.OK))
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
        dialog = Gtk.FileChooserDialog(
            "Open...",
            self.win,
            Gtk.FileChooserAction.OPEN,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK))
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

    def do_add_spectrum(self, *_ignore):
        """Imports a spectrum file and adds it to the current container."""
        dialog = Gtk.FileChooserDialog(
            "Import data...",
            self.win,
            Gtk.FileChooserAction.OPEN,
            ("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK))
        dialog.set_select_multiple(True)
        dialog.add_filter(SimpleFileFilter(
            "all files", ["*.xym", "*.txt", "*.xy"]))
        dialog.add_filter(SimpleFileFilter(".xym", ["*.xym"]))
        dialog.add_filter(SimpleFileFilter(".txt", ["*.txt"]))

        spectra = []
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for fname in dialog.get_filenames():
                if fname.split(".")[-1] in ["xym", "txt"]:
                    spectra.extend(self.parser.parse_spectrum_file(fname))
                elif fname.split(".")[-1] in ["xy"]:
                    print("not yet implemented")
                else:
                    print("file {} not recognized".format(fname))
            self.s_container.extend(spectra)
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

    def do_edit_spectrum(self, *_ignore):
        """Edits spectrum spectrum."""
        spectra = self.win.get_selected_spectra()
        if not spectra:
            return
        dialog = EditSpectrumDialog(self.win, spectra)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.change_values()
        dialog.destroy()

    def do_quit(self, *_ignore):
        """Quit program, write to config file."""
        xsize, ysize = self.win.get_size()
        xpos, ypos = self.win.get_position()
        __config__.set("window", "xsize", str(xsize))
        __config__.set("window", "ysize", str(ysize))
        __config__.set("window", "xpos", str(xpos))
        __config__.set("window", "ypos", str(ypos))
        cfg_name = __config__.get("general", "conf_filename")
        with open(cfg_name, "w") as cfg_file:
            __config__.write(cfg_file)
        self.quit()


class MainWindow(Gtk.ApplicationWindow):
    """ main window composed mainly of treeview and mpl canvas """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, app):
        self.app = app
        self.app.s_container.subscribe(self.container_callback)
        super().__init__(title=__appname__, application=app)
        self.connect("delete-event", self.app.do_quit)

        basedir = __config__.get("general", "basedir")
        xsize = int(__config__.get("window", "xsize"))
        ysize = int(__config__.get("window", "ysize"))
        xpos = int(__config__.get("window", "xpos"))
        ypos = int(__config__.get("window", "ypos"))
        self.set_default_size(xsize, ysize)
        self.move(xpos, ypos)
        self.set_icon_from_file(os.path.join(basedir, "icons/logo.svg"))

        actions = (
            ("about", self.do_about),
            ("show_selected", self.do_show_selected),
            ("debug", self.do_debug))
        for (name, callback) in actions:
            simple = Gio.SimpleAction.new(name, None)
            simple.connect("activate", callback)
            self.add_action(simple)

        context_actions = [
            ("Show selected", self.do_show_selected),
            ("Edit spectrum", self.app.do_edit_spectrum),
            ("Delete regions", self.do_delete_regions),
            ("debug", self.do_debug)]

        self.toolbar = ToolBar(self.app, self)
        self.canvasbox = CanvasBox(self.app, self)
        self.mpl_navbar = self.canvasbox.navbar
        self.cview = ContainerView(
            self.app.s_container, attrs=["name", "notes"], hide_headers=False)
        self.cview.menu = ContainerContextMenu(self.cview, context_actions)
        self.cview.menu.set_doubleclick_action(*context_actions[0])
        self.filterbar = TreeViewFilterBar(
            self.cview, "Notes", hide_combo=True)
        self.spectrum_settings = SpectrumSettings(self)
        self.rview = RegionManager(self)

        self.build_window()

    def build_window(self):
        """Pack the widgets into boxes."""
        cviewbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scrollable = Gtk.ScrolledWindow()
        scrollable.set_property("min-content-width", 300)
        scrollable.add(self.cview)
        cviewbox.pack_start(self.filterbar, False, False, 2)
        cviewbox.pack_start(scrollable, True, True, 2)
        cviewbox.pack_start(self.spectrum_settings, False, False, 2)

        vpanes = Gtk.VPaned()
        vpanes.pack1(cviewbox, True, False)
        self.rview.set_size_request(-1, 400)
        vpanes.pack2(self.rview, False, False)
        vpanes.set_wide_handle(True)

        hpanes = Gtk.HPaned()
        hpanes.shrink = False
        hpanes.pack1(vpanes, False, False)
        hpanes.pack2(self.canvasbox, True, False)

        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        masterbox.pack_start(self.toolbar, False, False, 0)
        masterbox.pack_start(hpanes, True, True, 0)
        self.add(masterbox)

    def do_about(self, *_args, **kwargs):
        """Show "About" dialog."""
        if "logo_path" in kwargs:
            logo_path = kwargs["logo_path"]
        else:
            logo_path = os.path.join(
                __config__.get("general", "basedir"), "icons/logo.svg")
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

    @staticmethod
    def message(string):
        """Message to be displayed to the user."""
        print(string)

    def do_debug(self, *_ignore):
        """Allows for testing stuff from GUI."""
        region = self.get_selected_region()
        region.fit()

    def do_show_rsf(self, *_ignore):
        """Calls the canvasbox method to show rsf values in plot."""
        self.canvasbox.show_rsf()

    def do_get_span(self, callback):
        """Gets a span from the user."""
        self.canvasbox.get_span(callback)

    def do_create_region(self, *_ignore):
        """Creates a region through the canvasbox.get_span method."""
        spectra = self.get_selected_spectra()
        if len(spectra) != 1:
            self.message("More than one spectrum selected")
            return
        self.mpl_navbar.disable()
        def create_region(emin, emax):
            """Creates a new region, callback for CanvasBox.get_span."""
            spectra[0].add_region(emin=emin, emax=emax)
        self.canvasbox.get_span(create_region, linewidth=2, edgecolor="blue")

    def do_delete_regions(self, *_ignore):
        """Deletes regions of selected spectra."""
        spectra = self.get_selected_spectra()
        for spectrum in spectra:
            spectrum.clear_regions()
        self.set_selected_spectra(spectra)

    def do_create_peak(self, *_ignore):
        """Lets the user draw a peak and creates a peak object from that."""
        def create_peak(center, height, angle):
            """Callback for CanvasBox.draw_peak."""
            region = self.get_selected_region()
            height = height - region.background_from_energy(center)
            fwhm = np.tan(np.deg2rad(angle)) * height
            region.add_peak(height=height, center=center, fwhm=fwhm)
        self.mpl_navbar.disable()
        self.canvasbox.draw_peak(create_peak)

    def do_show_selected(self, *_ignore):
        """Plots spectra that are selected in the SpectrumView."""
        spectra = self.get_selected_spectra()
        self.app.s_container.show_only(spectra)
        self.spectrum_settings.set_spectra(spectra)
        # TODO workaround: this counters the cview.amend() focus shift
        self.set_selected_spectra(spectra)

    def get_selected_spectra(self, *_ignore):
        """Returns the spectra currently selected in the SpectrumView."""
        return self.cview.get_selected_spectra()

    def set_selected_spectra(self, spectra, *_ignore):
        """Sets the selection."""
        self.cview.set_selected_spectra(spectra)

    def get_selected_region(self, *_ignore):
        """Returns the spectra currently selected in the RegionManager."""
        return self.rview.get_selected_region()

    def refresh(self, keepaxes=True, rview=True, canvas=True):
        """Refreshes rview and canvas."""
        # print("refresh")
        if rview:
            spectra = self.get_selected_spectra()
            if len(spectra) == 1:
                self.rview.set_spectrum(spectra[0])
            else:
                self.rview.set_spectrum(None)
        if canvas:
            self.canvasbox.refresh(keepaxes)

    def container_callback(self, keyword, _obj, **kwargs):
        """Catches everything important from the SpectrumContainer."""
        if keyword in ("changed_spectrum", "changed_region"):
            dontkeep_list = ("bgtype", "norm")
            keep_list = ("emin", "emax", "smoothness", "calibration")
            altered_list = ( #dontkeep_list + keep_list + (
                "name", "notes", "eis_region", "fname", "sweeps", "dwelltime",
                "passenergy")
            if any([attr in kwargs for attr in dontkeep_list]):
                self.refresh(keepaxes=False)
                self.app.s_container.altered = True
            elif any([attr in kwargs for attr in keep_list]):
                self.refresh(keepaxes=True)
                self.app.s_container.altered = True
            elif any([attr in kwargs for attr in altered_list]):
                self.app.s_container.altered = True

        elif keyword in ("clear_container", "plot"):
            self.refresh(keepaxes=False)

        elif keyword in ("remove_spectrum", "add_region", "remove_region",
                         "add_peak", "remove_peak", "fit", "changed_peak"):
            self.refresh(keepaxes=True)


class ToolBar(Gtk.Toolbar):
    """Main toolbar for file operations."""
    def __init__(self, app, parent):
        super().__init__()
        self.app = app
        self.parent = parent
        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        self.toolitems = (
            ("document-new", self.app.do_new),
            ("document-save", self.app.do_save),
            ("document-save-as", self.app.do_save_as),
            ("document-open", self.app.do_open_project),
            (None, None),
            ("list-add", self.app.do_add_spectrum),
            ("list-remove", self.app.do_remove_spectrum),
            (None, None),
            (os.path.join(
                __config__.get("general", "basedir"), "icons/atom_lib.png"),
             self.parent.do_show_rsf))
        for icon_name, callback in self.toolitems:
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
            tbutton.connect("clicked", callback)
