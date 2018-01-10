"""Provides a Spectrum class that stores all spectrum relevant data and
metadata. Also provides SpectrumContainer, a list containing Spectrums
and providing callback connection for changing Spectrums."""

import uuid

import numpy as np

import npl.processing as proc


class Spectrum(object):
    """Stores spectrum data."""
    # pylint: disable=access-member-before-definition, no-member
    # pylint: disable=attribute-defined-outside-init
    _titles = {
        "name": "Name",
        "notes": "Notes",
        "eis_region": "Region",
        "fname": "File name",
        "sweeps": "Sweeps",
        "dwelltime": "Dwell [s]",
        "passenergy": "Pass [eV]"}
    _defaults = {
        "sid": int(uuid.uuid4()) & (1<<64)-1,
        "visibility": "",
        "name": "",
        "notes": "",
        "eis_region": "",
        "fname": "",
        "sweeps": 0,
        "dwelltime": 0,
        "passenergy": 0,
        "regions": None,
        "smoothness": 0,
        "calibration": 0,
        "norm": 0,
        "_processed_energy": (None, None),
        "_processed_intensity": (None, None)}
    attrs = sorted(list(_defaults.keys()))

    def __init__(self, **kwargs):
        self._observers = []
        for attr in ("energy", "intensity"):
            if attr not in kwargs:
                raise ValueError("Missing property {}".format(attr))
        self._energy = kwargs["energy"]
        self._intensity = kwargs["intensity"]

        for (attr, default) in self._defaults.items():
            if default is None:
                default = []
            if attr in kwargs and kwargs[attr] is not None:
                setattr(self, attr, kwargs[attr])
            else:
                setattr(self, attr, default)

        if not self.name and self.eis_region:
            self.name = "(R {})".format(self.eis_region)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in self._titles:
            for callback in self._observers:
                callback("set", spectrum=self, attr=name, value=value)
        if name in ("smoothness", "calibration", "norm"):
            self.reprocess()

    def subscribe(self, callback):
        """Bind a new callback to this."""
        self._observers.append(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)

    def plot(self):
        """Switch plotting flag on.
        b: plot background
        d: plot spectrum (-> default)
        r: plot region markers"""
        self.visibility += "bdr"

    def unplot(self):
        """Switch plotting flag off."""
        self.visibility = self.visibility.replace("d", "")
        self.visibility = self.visibility.replace("r", "")
        self.visibility = self.visibility.replace("b", "")

    @property
    def intensity(self):
        """Spectrum intensity, including possible processing."""
        if self.smoothness == 0 and self.norm == 0:
            return self._intensity
        if self._processed_intensity[0] is None:
            intensity = self._intensity
            intensity = proc.normalize(intensity, self.norm)
            intensity = proc.moving_average(intensity, self.smoothness)
            self._processed_intensity = ("unchanged", intensity)
        return self._processed_intensity[1]

    @property
    def energy(self):
        """Spectrum energy, including calibration."""
        if self.calibration == 0:
            return self._energy
        if self._processed_energy[0] is None:
            energy = self._energy
            energy = proc.calibrate(energy, self.calibration)
            self._processed_energy = ("unchanged", energy)
        return self._processed_energy[1]

    def reprocess(self):
        """Next time self.energy and self.intensity are called, all processing
        is done anew."""
        self._processed_energy = (None, None)
        self._processed_intensity = (None, None)
        if hasattr(self, "regions"):
            for region in self.regions:
                region.reprocess()

    @staticmethod
    def title(attr):
        """Returns the user friendly string for an attribute."""
        if attr in Spectrum._titles:
            return Spectrum._titles[attr]
        return attr

    def __eq__(self, other):
        """ for testing equality """
        if self.sid == other.sid:
            return True
        return False
        # for attr in self.__dict__:
        #     if attr[0] == "_" or attr == "intensity" or attr == "energy":
        #         if attr != "_intensity" and attr != "_energy":
        #             continue
        #     try:
        #         if (isinstance(getattr(self, attr), np.ndarray)
        #                 or isinstance(getattr(other, attr), np.ndarray)):
        #             if (getattr(self, attr) != getattr(other, attr)).all():
        #                 return False
        #         elif getattr(self, attr) != getattr(other, attr):
        #             return False
        #     except AttributeError:
        #         return False
        # return True


class Region(object):
    """A region is a part of a spectrum."""
    # pylint: disable=access-member-before-definition, no-member
    # pylint: disable=attribute-defined-outside-init
    bgtypes = ("none", "linear", "shirley")
    _defaults = {"sid": int(uuid.uuid4()) & (1<<64)-1,
                 "name": "",
                 "bgtype": "shirley",
                 "_energy": (None, None),
                 "_background": (None, None),
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

        if not self.name:
            self.name = "Region {}".format(len(self.spectrum.regions) + 1)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ("emin", "emax"):
            self._background = "changed"
            self._energy = "changed"

    @property
    def background(self):
        """Calculates correct background on the fly."""
        if self.bgtype == "none":
            return None
        if not self._background[0] == self.bgtype:
            self._background = (self.bgtype, self.calculate_background())
        return self._background[-1]

    @property
    def energy(self):
        """Cuts out the energy from the overlaying spectrum."""
        if self._energy[0] != "unchanged":
            idx1, idx2 = sorted([
                np.searchsorted(self.spectrum.energy, self.emin),
                np.searchsorted(self.spectrum.energy, self.emax)])
            self._energy = ("unchanged", self.spectrum.energy[idx1:idx2])
        return self._energy[1]

    def reprocess(self):
        """Recalculate background etc at next occasion."""
        self._background = (None, None)
        self._energy = (None, None)

    def calculate_background(self):
        """Returns background subtracted intensity."""
        # pylint: disable=too-many-locals
        idx1, idx2 = sorted([np.searchsorted(self.spectrum.energy, self.emin),
                             np.searchsorted(self.spectrum.energy, self.emax)])
        energy = self.spectrum.energy[idx1:idx2]
        intensity = self.spectrum.intensity[idx1:idx2]

        if self.bgtype == "linear":
            background = np.linspace(intensity[0], intensity[-1], len(energy))
        elif self.bgtype == "shirley":
            background = proc.shirley(energy, intensity)
        else:
            background = None
        return background


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
        return None

    def get_idx_by_sid(self, sid):
        """Returns spectrum with the matching uuid."""
        for idx, spectrum in enumerate(self):
            if spectrum.sid == sid:
                return (idx, None)
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
            self.altered = True
