#!/usr/bin/python3.5

#import sys
#import os
#import warnings
#import time
import matplotlib as mpl
#from matplotlib.backends.backend_pgf import FigureCanvasPgf
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
        self.enabled = False


class Plotter:
    def __init__(self):
        self.fig = plt.figure()
        self.ax = self.fig.add_axes([0.15, 0.2, 0.8, 0.7])
        self.spectra = []

    def axrange(self, x_1, x_2, y_1, y_2):
        """set axes"""
        self._ax.axis([x_1, x_2, y_1, y_2])

    def show_spectra(self):
        for spectrum in self.spectra:
            if spectrum.enabled:
                print(spectrum.notes)
                self.ax.plot(spectrum.energy, spectrum.intensity,
                             label=spectrum.notes)
        return self.fig


