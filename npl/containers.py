"""Provides a Spectrum class that stores all spectrum relevant data and
metadata. Also provides SpectrumContainer, a list containing Spectrums
and providing callback connection for changing Spectrums."""

import uuid

import numpy as np


class Spectrum(object):
    """Stores spectrum data.""" #TODO: incorporate regions into db
    # pylint: disable=access-member-before-definition, no-member
    # pylint: disable=attribute-defined-outside-init
    _titles = {"name": "Name",
               "notes": "Notes",
               "eis_region": "Region",
               "fname": "File name",
               "sweeps": "Sweeps",
               "dwelltime": "Dwell [s]",
               "passenergy": "Pass [eV]"}
    _defaults = {"sid": int(uuid.uuid4()) & (1<<64)-1,
                 "visibility": "",
                 "name": "",
                 "notes": "",
                 "eis_region": "",
                 "fname": "",
                 "sweeps": 0,
                 "dwelltime": 0,
                 "passenergy": 0,
                 "energy": [],
                 "intensity": [],
                 "regions": []}
    attrs = sorted(list(_defaults.keys()))

    def __init__(self, **kwargs):
        self._observers = []
        for attr in ("energy", "intensity"):
            if attr not in kwargs:
                raise ValueError("Missing property {}".format(attr))
        for (attr, default) in self._defaults.items():
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs.get(attr, default))
            else:
                setattr(self, attr, default)
        if not self.name and self.eis_region:
            self.name = "(R {})".format(self.eis_region)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name != "visibility":
            for callback in self._observers:
                callback("set", spectrum=self, attr=name, value=value)

    def subscribe(self, callback):
        """Bind a new callback to this."""
        self._observers.append(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)

    def plot(self):
        """Switch plotting flag on."""
        self.visibility += "dr"

    def unplot(self):
        """Switch plotting flag off."""
        self.visibility = self.visibility.replace("d", "")
        self.visibility = self.visibility.replace("r", "")

    @staticmethod
    def title(attr):
        """Returns the user friendly string for an attribute."""
        if attr in Spectrum._titles:
            return Spectrum._titles[attr]
        return None

    def __eq__(self, other):
        """ for testing equality """
        for attr in self.__dict__:
            try:
                if (isinstance(getattr(self, attr), np.ndarray)
                        or isinstance(getattr(other, attr), np.ndarray)):
                    if (getattr(self, attr) != getattr(other, attr)).all():
                        return False
                elif getattr(self, attr) != getattr(other, attr):
                    return False
            except AttributeError:
                return False
        return True


class Region(object):
    """A region is a part of a spectrum."""
    _defaults = {"sid": int(uuid.uuid4()) & (1<<64)-1,
                 "name": "",
                 "emin": None,
                 "emax": None,
                 "spectrum": None}
    def __init__(self, **kwargs):
        self._observers = []
        for attr in ("spectrum", "emin", "emax"):
            if attr not in kwargs:
                raise TypeError("Missing property {}".format(attr))
        for (attr, default) in self._defaults.items():
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs.get(attr, default))
            else:
                setattr(self, attr, default)

    def subtract_background(self):
        """Returns background subtracted intensity."""
        pass

    def change_range(self, emin, emax):
        """Changes range to emin, emax."""
        pass


class Peak(object):
    """This object fits a peak in the real spectrum and is defined as part of
    a Region."""
    _defaults = {"sid": int(uuid.uuid4()) & (1<<64)-1,
                 "name": "",
                 "region": None,
                 "spectrum": None}
    def __init__(self, **kwargs):
        self._observers = []
        for attr in ("region",):
            if attr not in kwargs:
                raise TypeError("Missing property {}".format(attr))
        for (attr, default) in self._defaults.items():
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs.get(attr, default))
            else:
                setattr(self, attr, default)

    def set_constraint(self, constraint, value):
        """Sets a constraint for peak fitting."""
        pass

    def set_function(self, func):
        """Sets the fitting function."""
        pass


class SpectrumContainer(list):
    """ parses database for convenient use from the UI """
    spectrum_attrs = ["name", "sid", "visibility", "name", "notes",
                      "eis_region", "fname", "sweeps", "dwelltime",
                      "passenergy", "energy", "intensity"]
    def __init__(self):
        super().__init__()
        self.observers = []
        self.altered = True
        self.title = Spectrum.title

    def get_spectrum_by_sid(self, sid):
        """Returns spectrum with the matching uuid."""
        for spectrum in self:
            if spectrum.sid == sid:
                return spectrum
            for region in spectrum.regions:
                if region.sid == sid:
                    return region
        return None

    def get_idx_by_sid(self, sid):
        """Returns spectrum with the matching uuid."""
        for idx, spectrum in enumerate(self):
            if spectrum.sid == sid:
                return (idx, None)
            for idx2, region in enumerate(spectrum.regions):
                if region.sid == sid:
                    return (idx, idx2)
        return None

    def show_only(self, spectra_to_show):
        """ sets all visibility values to None except for one """
        if isinstance(spectra_to_show, Spectrum):
            spectra_to_show = [spectra_to_show]
        for spectrum in self:
            if spectrum in spectra_to_show:
                spectrum.plot()
            else:
                spectrum.unplot()

    def extend(self, spectra):
        for spectrum in spectra:
            self.append(spectrum)

    def append(self, spectrum):
        super().append(spectrum)
        spectrum.subscribe(self.spectrum_callback)
        idx = self.index(spectrum)
        for callback in self.observers:
            callback("append", spectrum=spectrum, index=idx)

    def remove(self, spectrum):
        idx = self.index(spectrum)
        for callback in self.observers:
            callback("remove", spectrum=spectrum, index=idx)
        super().remove(spectrum)

    def clear(self):
        for callback in self.observers:
            callback("clear")
        super().clear()

    def subscribe(self, callback):
        """Bind a new callback of class_ to this."""
        self.observers.append(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self.observers.remove(callback)

    def spectrum_callback(self, keyword, **kwargs):
        """Manages signals from single spectra."""
        if keyword == "set":
            for callback in self.observers:
                spectrum = kwargs["spectrum"]
                attr = kwargs["attr"]
                value = kwargs["value"]
                callback("amend", spectrum=spectrum, attr=attr, value=value)
