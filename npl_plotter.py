#!/usr/bin/python3.5
"""this module makes calculations and populates the canvas"""

# import matplotlib as mpl
# from matplotlib.backends.backend_pgf import FigureCanvasPgf
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo
import matplotlib.pyplot as plt
import numpy as np
import deepdish as dd
import re
import os
# from lmfit.models import PseudoVoigtModel
# from cycler import cycler

BASEDIR = "/home/simon/npl/"
SETTINGS_FOLDER = os.path.join(BASEDIR, ".npl/")

def unpack_eistxt(fname):
    splitregex = re.compile("^Region.*")
    splitcounter = 0
    with open(fname, "r") as eisfile:
        xyfile = open(SETTINGS_FOLDER + os.path.basename(fname) + "-"
                      + str(splitcounter).zfill(2) + '.xym', 'w')
        for line in eisfile:
            if re.match(splitregex, line):
                splitcounter += 1
                print(SETTINGS_FOLDER + os.path.basename(fname) + "-"
                              + str(splitcounter).zfill(2) + '.xym')
                xyfile = open(SETTINGS_FOLDER + os.path.basename(fname) + "-"
                              + str(splitcounter).zfill(2) + '.xym', 'w')
            xyfile.write(line)
    fnamelist = []
    for i in range(0, splitcounter+1):
        xym_fname = (SETTINGS_FOLDER + os.path.basename(fname) + "-"
                     + str(i).zfill(2) + '.xym')
        if os.stat(xym_fname).st_size != 0:
            fnamelist.append(xym_fname)
    return fnamelist


class Spectrum(dict):
    """represents a single XPS spectrum with metadata"""
    def __init__(self, data):
        super().__init__()
        if isinstance(data, str):
            if data.split(".")[-1] == "xym":
                self.get_meta_from_xyfile(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                self[key] = value

    def get_meta_from_xyfile(self, fname):
        """reads meta from a Omicron split txt file"""
        self["Filename"] = fname
        self["Energy"], self["Intensity"] = np.loadtxt(self["Filename"],
                                                       delimiter="\t",
                                                       skiprows=5,
                                                       unpack=True)
        self["Energy"] = self["Energy"][::-1]
        self["Intensity"] = self["Intensity"][::-1]

        with open(self["Filename"], "r") as xyfile:
            fourlines = [x.split("\t") for i, x in enumerate(xyfile)
                         if i in range(0, 4)]
        self["Region"] = fourlines[1][0]
        self["E_max"] = str(max(self["Energy"]))
        self["E_min"] = str(min(self["Energy"]))
        self["Resolution"] = str(self["Energy"][1] - self["Energy"][0])
        self["Sweeps"] = fourlines[1][6]
        self["Dwelltime"] = fourlines[1][7]
        self["Notes"] = fourlines[1][12]
        self["Visible"] = True
        self["Name"] = str()

    def treeview_strings(self):
        """gives values to a liststore"""
        return (self["Visible"], self["Name"], self["Notes"], str(round(float(self["E_min"]),1)),
                str(round(float(self["E_max"]), 1)), str(self["Sweeps"]),
                str(round(float(self["Dwelltime"]), 2)), self)

    def values_by_keylist(self, keys):
        values = []
        for key in keys:
            values.append(self[key])
        return values

    def subtract_shirley(self, shirley):
        """subtracts shirley background from self.intensity"""
        point_number = len(self.energy)
        e_start = self.intensity[0]
        e_end = self.intensity[-1]
        spacing = (self.energy[-1] - self.energy[0]) / (point_number - 1)
        background = e_end * np.ones(point_number)
        integral = np.zeros(point_number)
        crit_list = np.array([])
        spectrum_no_bg = self.intensity - background
        ysum = spectrum_no_bg.sum()-np.cumsum(spectrum_no_bg)
        for i in range(0, point_number):
            integral[i] = spacing * (ysum[i] - 0.5 * (spectrum_no_bg[i] +
                                                      spectrum_no_bg[-1]))
        background = (e_start - e_end) * integral / integral[0] + e_end
        spectrum_no_bg = self.intensity - background
        crit_list = np.insert(crit_list, 0, integral[0])
        crit_ratio = np.inf
        timeout_start = time.time()
        while crit_ratio > shirley and time.time() < timeout_start + 2:
            integral = spacing * (spectrum_no_bg.sum() -
                                  np.cumsum(spectrum_no_bg))
            background = (e_start - e_end) * integral / integral[0] + e_end
            spectrum_no_bg = self.intensity - background
            crit_list = np.insert(crit_list, -1, integral[0])
            crit_ratio = abs((crit_list[-1] - crit_list[-2]) / crit_list[-2])
        self.intensity = spectrum_no_bg
        print('shirley_crit = ' + str(crit_ratio))
        return str(crit_ratio)


class Database(list):
    """contains Spectrum objects and manages them, also syncs with a given
    liststore that has the Specturm object itself as last element for
    identification"""
    def __init__(self, liststore=None, loadfrom=None):
        self.liststore = liststore

    def append(self, spectrum):
        super().append(spectrum)
        if self.liststore is not None:
            self.liststore.append(spectrum.treeview_strings())

    def clear(self):
        super().clear()
        if self.liststore is not None:
            self.liststore.clear()

    def remove(self, spectrum, treeiter=None):
        super().remove(spectrum)
        if self.liststore is not None:
            if treeiter is not None:
                self.liststore.remove(treeiter)
            else:
                for row in self.liststore:
                    if row[-1] == spectrum:
                        self.liststore.remove(row.iter)
            print("--- " + spectrum["Filename"])

    def dump(self, fname):
        """dumps self into .h5 file with deepdish"""
        dd.io.save(fname, self)

    def load(self, fname):
        """loads itself from a .h5 file with deepdish"""
        self.clear()
        self.add(*dd.io.load(fname))

    def return_by_key(self, key, value):
        """returns a list of spectra that have value value in key key"""
        found_spectra = [spectrum for spectrum in self
                         if np.all(spectrum[key] == value)]
        return found_spectra

    def add(self, *spectra):
        """adds Spectrum to self from a list of either files containing single
        spectrum or dicts"""
        for specdata in spectra:
            spectrum = Spectrum(specdata)
            if self.return_by_key("Intensity", spectrum["Intensity"]):
                print(spectrum["Filename"] + " already loaded")
            else:
                self.append(spectrum)
                print("+++ " + spectrum["Filename"])

    def remove_by_key(self, key, value):
        """removes spectra found by return_by_key"""
        for spectrum in self.return_by_key(key, value):
            self.remove(spectrum)


class RSFlib(list):
    """stores relative sensitivity factors, example: [O, 1s, 532, 2.93, Mg, r]"""
    def __init__(self):
        with open(os.path.join(BASEDIR, "rsf.lib"), "r") as libfile:
            for line in libfile:
                entry = line.split("\t")
                if entry[9] == "Any":
                    entry[8] = 1
                self.append([entry[0], entry[1], float(entry[5]),
                             float(entry[8]), entry[9]])
        self.selected = []
        self.selected_names = []
        self.colorcount = 0
        self.sources = ("Mg", "Any")

    def set_source(self, source):
        self.sources = (source, "Any")

    def select(self, element):
        self.selected_names.append(element)
        for entry in self:
            if entry[0] == element and entry[4] in self.sources:
                entry.append("bgrcmy"[self.colorcount])
                self.selected.append(entry)
        self.colorcount += 1
        if self.colorcount > 5:
            self.colorcount = 0

    def deselect(self, element):
        self.selected_names.remove(element)
        for entry in self.selected:
            if entry[0] == element:
                self.selected.remove(entry)

    def flush(self):
        self.selected = []
        self.selected_names = []
        self.colorcount = 0
        
    def give_data(self):
        return self.selected

    def give_selected(self):
        selstring = " ".join(self.selected_names)
        return selstring


class Plotter:
    """does the plotting stuff"""
    def __init__(self, database, rsflib):
        self.fig = plt.figure(figsize=(10, 10), dpi=80)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.database = database
        self.canvas = FigureCanvasGTK3Cairo(self.fig)

        self.x_1 = np.inf
        self.x_2 = -np.inf
        self.y_1 = np.inf
        self.y_2 = -np.inf

        self.rsflib = rsflib
        self.ax.tick_params(axis='both', which='major', pad=-20)

    def axrange(self):
        """set axes"""
        if np.all(np.isfinite([self.x_1, self.x_2, self.y_1, self.y_2])):
            self.ax.axis([self.x_1, self.x_2, self.y_1, self.y_2])

    def plot_spectra(self, keepaxes=False):
        """plots all spectra in the database that are enabled"""
        if keepaxes:
            self.x_1, self.x_2, self.y_1, self.y_2 = self.ax.axis()
        self.ax.cla()

        for spectrum in self.database:
            if spectrum["Visible"]:
                self.ax.plot(spectrum["Energy"], spectrum["Intensity"],
                             label=spectrum["Notes"], c="k", lw=1)

        self.make_pretty()
        if not keepaxes:
            self.fit_axranges()
        else:
            self.axrange()
        self.canvas.draw_idle()

    def plot_rsf(self):
        """plots relative sensitivity factors"""
        rsfs = self.rsflib.give_data()
        if len(rsfs) == 0:
            return
        normfactor = self.y_2 / max([x[3] for x in rsfs]) * 0.8
        for rsf in rsfs:
            self.ax.plot([rsf[2], rsf[2]], [0, rsf[3]*normfactor], c=rsf[5],
                         lw=1)
            self.ax.annotate(" ".join([rsf[0], rsf[1]]),
                             xy=[rsf[2], rsf[3]*normfactor],
                             textcoords="data")

    def make_pretty(self):
        plt.yticks(rotation='vertical')
        self.ax.xaxis.get_major_ticks()[0].set_visible(False)
        self.ax.xaxis.get_major_ticks()[-1].set_visible(False)
        self.ax.yaxis.get_major_ticks()[0].set_visible(False)
        self.ax.yaxis.get_major_ticks()[-1].set_visible(False)

    def fit_axranges(self, keepaxes=False):
        self.x_1 = np.inf
        self.x_2 = -np.inf
        self.y_1 = np.inf
        self.y_2 = -np.inf
        for spectrum in self.database:
            if spectrum["Visible"]:
                self.x_1 = min(self.x_1, min(spectrum["Energy"]))
                self.x_2 = max(self.x_2, max(spectrum["Energy"]))
                self.y_1 = min(self.y_1, min(spectrum["Intensity"]))
                self.y_2 = max(self.y_2, max(spectrum["Intensity"]))
        self.y_2 *= 1.05
        self.axrange()

    def refresh(self, keepaxes=False):
        """refreshes canvas"""
        self.plot_spectra(keepaxes)
        self.plot_rsf()
        self.canvas.draw()
