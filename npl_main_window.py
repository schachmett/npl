#!/usr/bin/python3.5

import npl_plotter
import gi
gi.require_version('Gtk', '3.0')
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from gi.repository import Gtk

def main():
    mc = MainClass()
    mc.mw.connect("delete-event", Gtk.main_quit)
    mc.mw.set_default_size(500,500)
    #mw.set_border_width(10)
    mc.mw.show_all()
    Gtk.main()


class MainClass():
    def __init__(self):
        self.plotter = npl_plotter.Plotter()
        
        self.mw = Gtk.Window(title="npl")
        self.mw.connect("delete-event", Gtk.main_quit)
        masterbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.mw.add(masterbox)
        
        toolbar = self.create_toolbar()
        masterbox.pack_start(toolbar, False, False, 0)

        contentpanes = Gtk.HPaned()
        masterbox.pack_start(contentpanes, True, True, 0)
        butt = Gtk.Button()
        butt.set_size_request(100,100)
        contentpanes.add1(butt)
        
        self.plotter.show_spectra()
        self.plotter.canvas.draw()
        contentpanes.add2(self.plotter.canvas)


    def draw_plot(self):
        pass
        
    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        context = toolbar.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        
        self.addbutton = Gtk.ToolButton()
        self.addbutton.set_icon_name("list-add")
        toolbar.insert(self.addbutton, 0)
        self.addbutton.connect("clicked", self.add_spectrum)
        return toolbar

    def add_spectrum(self, caller):
        dialog = Gtk.FileChooserDialog("Open...", self.mw,
                 Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL,
                 Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        xyfilter = Gtk.FileFilter()
        xyfilter.add_pattern("*.xy")
        xyfilter.set_name(".xy")
        dialog.add_filter(xyfilter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("selected " + dialog.get_filename())
            self.plotter.spectra.append(npl_plotter.Spectrum(dialog.get_filename()))
        else:
            print("nothing selected")
        dialog.destroy()
        
        #~ box = Gtk.VBox()
        #~ tbox = self.create_toolbox()
        #~ box.pack_start(tbox, True, True, 0)
        #~ slist = self.create_spectralist(self.list_of_spectra)
        #~ box.pack_start(slist, True, True, 0)
        #~ self.add(box)
        
        #~ self.pw = PlotWindow(self.list_of_spectra)
        #~ self.pw.connect("delete-event", self.close_plotwindow)

    #~ def create_toolbox(self):
        #~ toolbox = Gtk.Grid()
        #~ toolbox.set_column_spacing(10)

        #~ button1 = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.DIALOG)
        #~ button1.connect("clicked", self.get_file)
        #~ button2 = Gtk.Button.new_from_icon_name("system-run", Gtk.IconSize.DIALOG)
        #~ button2.connect("clicked", self.show_spectra)
        #~ toolbox.add(button1)
        #~ toolbox.add(button2)
        #~ return toolbox

    #~ def create_spectralist(self, spectra):
        #~ spectrabox = Gtk.VBox()
        #~ for spectrum in spectra:
            #~ hbox = Gtk.HBox(homogeneous=True, spacing=20)
            #~ hbox.pack_start(Gtk.Label(spectrum.notes), True, True, 0)
            #~ checkbox = Gtk.CheckButton("Enabled")
            #~ checkbox.set_active(False)
            #~ checkbox.connect("toggled", self.update_spectra, spectrum)
            #~ hbox.pack_start(checkbox, True, True, 0)
            #~ spectrabox.pack_start(hbox, True, True, 0)
        #~ return spectrabox

    #~ def show_spectra(self, callerwidget):
        #~ self.pw.refresh(self.list_of_spectra)
        
    #~ def update_spectra(self, button, spectrum):
        #~ spectrum.enabled = button.get_active()
        #~ self.pw.refresh(self.list_of_spectra)

    #~ def close_plotwindow(self, caller):
        #~ self.pw.__init__(list_of_spectra)
        #~ return True



#~ class PlotWindow(Gtk.Window):
    #~ def __init__(self, spectra):
        #~ Gtk.Window.__init__(self, title="Plot")
        #~ sw = Gtk.ScrolledWindow()
        #~ self.set_default_size(800,500)
        #~ self.add(sw)

        #~ self.plotter = npl_plotter.Plotter()
        #~ self.plotter.spectra = spectra
        #~ self.canvas = FigureCanvas(self.plotter.show_spectra())
        #~ self.canvas.set_size_request(800,500)
        #~ sw.add_with_viewport(self.canvas)

    #~ def refresh(self, spectra):
        #~ self.plotter.spectra = spectra
        #~ self.plotter.ax.cla()
        #~ self.plotter.show_spectra()
        #~ self.canvas.draw()

if __name__ == '__main__':
    main()
