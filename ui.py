#!/usr/bin/python3.5
"""this module manages the windows of npl"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import gtk
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
import db_manager
import plotter
import processing


class MainWindow(self):
	def __init__(self):
		pass
	
	def build_window(self):
		pass

	def refresh_treeview(self):
		pass

	def refresh_canvas(self):
		pass


class ToolBar(gtk.Toolbar):
	def __init__(self):
		pass

	def add_file(self):
		pass

	def delete_spectra(self):
		pass

	def load_project(self):
		pass

	def save_project(self):
		pass


class AnalBar():
	def __init__(self):
		pass


class SpectrumView(gtk.Box):
	def __init__(self):
		pass

	def refresh(self):
		pass

	def on_row_clicked(self):
		pass

	def on_col_edited(self):
		pass

	def on_spectrum_toggled(self):
		pass


class Canvas(gtk.Box):
	def __init__(self):
		pass

	def refresh(self):
		pass


class MPLNavBar(NavigationToolbar2GTK3):
	def __init__(self):
		pass
