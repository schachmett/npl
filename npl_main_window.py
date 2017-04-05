#!/usr/bin/python3.5

import npl_plotter
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas

def main():
	mw = MainWindow()
	#mw.set_default_size(400,200)
	mw.set_border_width(10)
	mw.show_all()
	Gtk.main()


class MainWindow(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, title="Settings")
		self.connect("delete-event", Gtk.main_quit)
		self.list_of_spectra = [npl_plotter.Spectrum("/home/simon/Dokumente/uni/masterarbeit/analyse/xps2/xy_data/2016-01-25_TiO2-001-a_cleaning-08.xy")]

		box = Gtk.VBox()
		tbox = self.create_toolbox()
		box.pack_start(tbox, True, True, 0)
		slist = self.create_spectralist(self.list_of_spectra)
		box.pack_start(slist, True, True, 0)
		self.add(box)
		
		self.pw = PlotWindow(self.list_of_spectra)

	def create_toolbox(self):
		toolbox = Gtk.Grid()
		toolbox.set_column_spacing(10)

		button1 = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.DIALOG)
		button1.connect("clicked", self.get_file)
		button2 = Gtk.Button.new_from_icon_name("system-run", Gtk.IconSize.DIALOG)
		button2.connect("clicked", self.show_spectra)
		toolbox.add(button1)
		toolbox.add(button2)
		return toolbox

	def create_spectralist(self, spectra):
		spectrabox = Gtk.VBox()
		for spectrum in spectra:
			hbox = Gtk.HBox(homogeneous=True, spacing=20)
			hbox.pack_start(Gtk.Label(spectrum.notes), True, True, 0)
			checkbox = Gtk.CheckButton("Enabled")
			checkbox.set_active(False)
			checkbox.connect("toggled", self.update_spectra, spectrum)
			hbox.pack_start(checkbox, True, True, 0)
			spectrabox.pack_start(hbox, True, True, 0)
		return spectrabox

	def get_file(self, callerwidget):
		dialog = Gtk.FileChooserDialog("Open...", self,
				 Gtk.FileChooserAction.OPEN,
				 (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
		xyfilter = Gtk.FileFilter()
		xyfilter.add_pattern("*.xy")
		xyfilter.set_name(".xy")
		dialog.add_filter(xyfilter)

		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			print("selected " + dialog.get_filename())
			self.list_of_spectra.append(npl_plotter.Spectrum(dialog.get_filename()))
		else:
			print("nothing selected")
		dialog.destroy()

	def show_spectra(self, callerwidget):
		self.pw.refresh(self.list_of_spectra)
		self.pw.show_all()
		
	def update_spectra(self, button, spectrum):
		if button.get_active():
			spectrum.enabled = True
		else:
			spectrum.enabled = False
		self.pw.refresh(self.list_of_spectra)



class PlotWindow(Gtk.Window):
	def __init__(self, spectra):
		Gtk.Window.__init__(self, title="Plot")
		sw = Gtk.ScrolledWindow()
		self.set_default_size(800,500)
		self.add(sw)

		self.plotter = npl_plotter.Plotter()
		self.plotter.spectra = spectra
		self.canvas = FigureCanvas(self.plotter.show_spectra())
		self.canvas.set_size_request(800,500)
		sw.add_with_viewport(self.canvas)

	def refresh(self, spectra):
		self.plotter.spectra = spectra
		self.plotter.ax.cla()
		self.plotter.show_spectra()
		self.canvas.draw()

if __name__ == '__main__':
    main()
