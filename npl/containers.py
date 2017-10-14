""" data containers """

import numpy as np


class SpectrumContainer(list):
    """ parses database for convenient use from the UI """
    # def __init__(self):
    #     super().__init__()

    def show_only(self, spectra_to_show):
        """ sets all visibility values to None except for one """
        if isinstance(spectra_to_show, Spectrum):
            spectra_to_show = [spectra_to_show]
        for spectrum in self:
            if spectrum in spectra_to_show:
                spectrum.plot()
            else:
                spectrum.unplot()


class Spectrum(dict):
    """ stores spectrum data as an object """
    essential_keys = ["Name", "Notes", "EISRegion", "Filename", "Sweeps",
                      "DwellTime", "PassEnergy", "Energy", "Intensity"]
    defaulting_dict = {"SpectrumID": None, "Visibility": None}

    def __init__(self, datadict):
        super().__init__()
        for key in self.essential_keys:
            if key not in datadict:
                raise ValueError("missing key for Spectrum "
                                 "init: {}".format(key))
            else:
                self[key] = datadict[key]
        for key in self.defaulting_dict:
            if key not in datadict:
                self[key] = self.defaulting_dict[key]
            else:
                self[key] = datadict[key]
        if not self["Name"]:
            self["Name"] = "(R {0})".format(self["EISRegion"])

    def plot(self):
        """ switch plotting flag on """
        self["Visibility"] = "default"

    def unplot(self):
        """ switch plotting flag off """
        self["Visibility"] = None

    def __eq__(self, other):
        """ for testing equality """
        for key in self.essential_keys + list(self.defaulting_dict.keys()):
            try:
                if (isinstance(self[key], np.ndarray) or
                        isinstance(other[key], np.ndarray)):
                    if (self[key] != other[key]).all():
                        return False
                elif self[key] != other[key]:
                    return False
            except KeyError:
                return False
        return True
