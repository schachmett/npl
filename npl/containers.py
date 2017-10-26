""" data containers """
# pylint: disable=C0413

import uuid

# import gi
# gi.require_version('Gtk', '3.0')
# from gi.repository import GObject
import numpy as np


class SpectrumContainer(list):
    """ parses database for convenient use from the UI """
    def __init__(self):
        super().__init__()
        self.observers = []
        self.altered = True

    def show_only(self, spectra_to_show):
        """ sets all visibility values to None except for one """
        if isinstance(spectra_to_show, Spectrum):
            spectra_to_show = [spectra_to_show]
        for spectrum in self:
            if spectrum in spectra_to_show:
                spectrum.plot()
            else:
                spectrum.unplot()

    def append(self, spectrum):
        super().append(spectrum)
        spectrum.bind(self, "spectrum_callback")
        idx = self.index(spectrum)
        for class_, callback in self.observers:
            getattr(class_, callback)("append", spectrum=spectrum, index=idx)

    def remove(self, spectrum):
        idx = self.index(spectrum)
        super().remove(spectrum)
        for class_, callback in self.observers:
            getattr(class_, callback)("remove", spectrum=spectrum, index=idx)

    def clear(self):
        super().clear()
        for class_, callback in self.observers:
            getattr(class_, callback)("clear")

    def bind(self, class_, callback):
        """Bind a new callback of class_ to this."""
        self.observers.append((class_, callback))

    def unbind(self, class_, callback):
        """Unbind the callback."""
        self.observers.remove((class_, callback))

    def spectrum_callback(self, keyword, **kwargs):
        """Manages signals from single spectra."""
        if keyword == "set":
            for class_, callback in self.observers:
                spectrum = kwargs["spectrum"]
                key = kwargs["key"]
                value = kwargs["value"]
                getattr(class_, callback)("amend", spectrum=spectrum, key=key,
                                          value=value)


class Spectrum(dict):
    """ stores spectrum data as an object """
    essential_keys = ["Name", "Notes", "EISRegion", "Filename", "Sweeps",
                      "DwellTime", "PassEnergy", "Energy", "Intensity"]
    defaulting_dict = {"SpectrumID": None, "Visibility": None}

    def __init__(self, datadict):
        super().__init__()
        self.observers = []
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
        self.uuid = uuid.uuid4()

    def set(self, key, value):
        """Value setter that calls all available callbacks."""
        self[key] = value
        for class_, callback in self.observers:
            getattr(class_, callback)("set", spectrum=self, key=key,
                                      value=value)

    def bind(self, class_, callback):
        """Bind a new callback of class_ to this."""
        self.observers.append((class_, callback))

    def unbind(self, class_, callback):
        """Unbind the callback."""
        self.observers.remove((class_, callback))

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
