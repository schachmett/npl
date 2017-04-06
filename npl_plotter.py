#!/usr/bin/python3.5

#import sys
#import os
#import warnings
#import time
import matplotlib as mpl
#from matplotlib.backends.backend_pgf import FigureCanvasPgf
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
#import re
#import argparse
#import json
#from lmfit.models import PseudoVoigtModel
#from cycler import cycler


class Spectrum:
    def __init__(self, fname):
        self.fname = fname
        self.energy, self.intensity = np.loadtxt(self.fname, delimiter="\t",
                                                 skiprows=5, unpack=True)
        self.energy = self.energy[::-1]
        self.intensity = self.intensity[::-1]

        with open(self.fname, 'r') as xyfile:
            fourlines = [x.split('\t') for i, x in enumerate(xyfile)
                         if i in range(0, 4)]
        self.region = int(fourlines[1][0])
        self.e_start = float(fourlines[1][3])
        self.e_end = float(fourlines[1][4])
        self.e_step = float(fourlines[1][5])
        self.sweeps = int(fourlines[1][6])
        self.dwell = float(fourlines[1][7])
        self.mode = fourlines[1][8]
        self.cae_crr = float(fourlines[1][9])
        self.mag = fourlines[1][10]
        self.notes = fourlines[1][12]
        self.enabled = True
        self.name = ""

    def treeview_strings(self):
        return self.name, self.notes


class Plotter:
    def __init__(self):
        self.fig = plt.figure(figsize=(10,10), dpi=100)
        self.ax = self.fig.add_axes([0.07, 0.05, 0.93, 0.95])
        self.spectra = [Spectrum("/home/simon/Dokumente/uni/masterarbeit/analyse/xps2/xy_data/2016-01-25_TiO2-001-a_cleaning-08.xy")]
        self.canvas = FigureCanvas(self.fig)
        plt.yticks(rotation='vertical')

    def axrange(self, x_1, x_2, y_1, y_2):
        """set axes"""
        self.ax.axis([x_1, x_2, y_1, y_2])

    def plot_spectra(self):
        for spectrum in self.spectra:
            if spectrum.enabled:
                self.ax.plot(spectrum.energy, spectrum.intensity,
                             label=spectrum.notes)


