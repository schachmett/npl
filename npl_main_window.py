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
        toolbar = MyToolBar(self)
        masterbox.pack_start(toolbar, False, False, 0)
        contentpanes = Gtk.HPaned()
        masterbox.pack_start(contentpanes, True, True, 0)
        
        butt = SpectrumList(self)
        contentpanes.add1(butt)
 #       butt.set_size_request(100,100)

        self.mycanvas = MyCanvas(self.plotter)
        contentpanes.add2(self.mycanvas)


class SpectrumList(Gtk.Box):
    def __init__(self, mainclass):
        super().__init__()
        self.mc = mainclass
        self.set_size_request(100,100)

class MyCanvas(Gtk.Box):
    def __init__(self, plotter):
        super().__init__()
        self.plotter = plotter
        self.pack_start(self.plotter.canvas, True, True, 0)
        self.plotter.plot_spectra()

    def draw_plot(self):
        self.plotter.ax.cla()
        self.plotter.plot_spectra()


class MyToolBar(Gtk.Toolbar):
    def __init__(self, mc):
        super().__init__()
        self.mc = mc
        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        
        self.addbutton = Gtk.ToolButton()
        self.addbutton.set_icon_name("list-add")
        self.insert(self.addbutton, 0)
        self.addbutton.connect("clicked", self.add_spectrum)

    def add_spectrum(self, caller):
        dialog = Gtk.FileChooserDialog("Open...", self.mc.mw,
                 Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL,
                 Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        xyfilter = Gtk.FileFilter()
        xyfilter.add_pattern("*.xy")
        xyfilter.set_name(".xy")
        dialog.add_filter(xyfilter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("selected " + dialog.get_filename())
            self.mc.plotter.spectra.append(npl_plotter.Spectrum(dialog.get_filename()))
        else:
            print("nothing selected")
        self.mc.mycanvas.draw_plot()
        dialog.destroy()

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

if __name__ == '__main__':
    main()
