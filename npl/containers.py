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
    # pylint: disable=too-many-instance-attributes
    titles = {
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
        "smoothness": 0,
        "calibration": 0,
        "norm": 0}
    attrs = sorted(list(_defaults.keys()))

    def __init__(self, **kwargs):
        super().__init__()
        self._observers = []
        for attr in ("energy", "intensity"):
            if attr not in kwargs:
                raise ValueError("Missing property {}".format(attr))

        self._energy = kwargs["energy"]
        self._intensity = kwargs["intensity"]
        self._processed_energy = (None, self._energy)
        self._processed_intensity = (None, self._intensity)
        self.regions = RegionList()

        for (attr, default) in self._defaults.items():
            setattr(self, attr, kwargs.get(attr, default))

        if not self.name and self.eis_region:
            self.name = "(R {})".format(self.eis_region)

    def __setattr__(self, name, value):
        if (hasattr(self, name)
                and name in ("smoothness", "norm", "calibration")
                and value != getattr(self, name)):
            self.reprocess()
        super().__setattr__(name, value)
        self.emit("set", attr=name, value=value)

    @property
    def intensity(self):
        """Spectrum intensity, including possible processing."""
        if self._processed_intensity[0] is None:
            intensity = self._intensity
            intensity = proc.normalize(intensity, self.norm)
            intensity = proc.moving_average(
                intensity, self.smoothness)
            self._processed_intensity = (True, intensity)
        return self._processed_intensity[1]

    @property
    def energy(self):
        """Spectrum energy, including calibration."""
        if self._processed_energy[0] is None:
            self._processed_energy = (True, self._energy + self.calibration)
        return self._processed_energy[1]

    def reprocess(self):
        """Next time self.energy and self.intensity are called, all processing
        is done anew."""
        self._processed_energy = (None, self._processed_energy[1])
        self._processed_intensity = (None, self._processed_intensity[1])
        self.emit("reprocess")

    def recalculate(self):
        """Calls self.energy and self.intensity after reprocessing."""
        self.reprocess()
        return self.energy, self.intensity

    def get_energy_at_maximum(self, span):
        """Returns the energy at the intensity maximum in a given energy
        span=(emin, emax)."""
        maxen = proc.get_energy_at_maximum(
            self._processed_energy[1], self._processed_intensity[1], span)
        return maxen

    def __eq__(self, other):
        """For testing equality."""
        if self.sid == other.sid:
            return True
        return False

    def plot(self):
        """Switch plotting flag on. b: plot background, d: plot spectrum
        (-> default), r: plot region markers"""
        self.visibility += "bdr"

    def unplot(self):
        """Switch plotting flags off."""
        self.visibility = ""

    def subscribe(self, callback):
        """Bind a new callback to this."""
        self._observers.append(callback)
        self.regions.subscribe(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)
        self.regions.unsubscribe(callback)

    def emit(self, keyword, **kwargs):
        """Emits to all obervers."""
        for callback in self._observers:
            callback(keyword, self, **kwargs)

    @staticmethod
    def title(attr):
        """Returns the user friendly string for an attribute."""
        if attr in Spectrum.titles:
            return Spectrum.titles[attr]
        return attr


class Region(object):
    """A region is a part of a spectrum."""
    # pylint: disable=access-member-before-definition, no-member
    # pylint: disable=attribute-defined-outside-init
    bgtypes = ("none", "shirley", "linear")
    _defaults = {
        "sid": int(uuid.uuid4()) & (1<<64)-1,
        "name": "",
        "emin": None,
        "emax": None,
        "spectrum": None,
        "_energy": (None, None),
        "_background": (None, None),
        "bgtype": "shirley"}

    def __init__(self, **kwargs):
        super().__init__()
        self._observers = []
        for attr in ("spectrum", "emin", "emax"):
            if attr not in kwargs:
                raise TypeError("Missing property {}".format(attr))

        for (attr, default) in self._defaults.items():
            setattr(self, attr, kwargs.get(attr, default))

        if not self.name:
            self.name = "Region {}".format(len(self.spectrum.regions) + 1)
        self.spectrum.subscribe(self.reprocess_callback)
        self.subscribe(self.reprocess_callback)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        self.emit("set", attr=name, value=value)
        if name in ("emin", "emax"):
            self._background = (None, None)
            self._energy = (None, None)

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
        if self._energy[0] is None:
            idx1, idx2 = sorted([
                np.searchsorted(self.spectrum.energy, self.emin),
                np.searchsorted(self.spectrum.energy, self.emax)])
            self._energy = ("unchanged", self.spectrum.energy[idx1:idx2])
        return self._energy[1]

    def reprocess_callback(self, keyword, obj, **kwargs):
        """Recalculate background etc at next occasion."""
        if type(obj).__name__ == "Spectrum" and keyword == "reprocess":
            self._background = (None, self._background[1])
            self._energy = (None, self._background[1])
        elif obj == self and keyword == "set":
            if kwargs["attr"] == "bgtype":
                self._background = (None, self._background[1])
                self._energy = (None, self._background[1])

    def calculate_background(self):
        """Returns background subtracted intensity."""
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

    def subscribe(self, callback):
        """Bind a new callback to this."""
        self._observers.append(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)

    def emit(self, keyword, **kwargs):
        """Emits to all obervers."""
        for callback in self._observers:
            callback(keyword, self, **kwargs)


class RegionList(list):
    """Contains regions, to be used by Spectrum class."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._observers = []

    def append(self, region):
        super().append(region)
        self.emit("append", region=region)
        for callback in self._observers:
            region.subscribe(callback)

    def remove(self, region):
        super().remove(region)
        self.emit("remove", region=region)

    def subscribe(self, callback):
        """Bind a new callback to this."""
        self._observers.append(callback)
        for region in self:
            region.subscribe(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)
        for region in self:
            region.unsubscribe(callback)

    def emit(self, keyword, **kwargs):
        """Emits to all obervers."""
        for callback in self._observers:
            callback(keyword, self, **kwargs)


# class Peak(object):
#     """This object fits a peak in the real spectrum and is defined as part of
#     a Region."""
#     _defaults = {"sid": int(uuid.uuid4()) & (1<<64)-1,
#                  "name": "",
#                  "region": None,
#                  "spectrum": None}
#     def __init__(self, **kwargs):
#         self._observers = []
#         for attr in ("region",):
#             if attr not in kwargs:
#                 raise TypeError("Missing property {}".format(attr))
#         for (attr, default) in self._defaults.items():
#             if attr in kwargs and kwargs[attr] is not None:
#                 setattr(self, attr, kwargs.get(attr, default))
#             else:
#                 setattr(self, attr, default)
#
#     def set_constraint(self, constraint, value):
#         """Sets a constraint for peak fitting."""
#         pass
#
#     def set_function(self, func):
#         """Sets the fitting function."""
#         pass


class SpectrumContainer(list):
    """ parses database for convenient use from the UI """
    spectrum_attrs = ["name", "sid", "visibility", "name", "notes",
                      "eis_region", "fname", "sweeps", "dwelltime",
                      "passenergy", "energy", "intensity"]
    def __init__(self):
        super().__init__()
        self._observers = []
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
        self.emit("plot")

    def append(self, spectrum):
        super().append(spectrum)
        idx = self.index(spectrum)
        self.emit("append", spectrum=spectrum, index=idx)
        for callback in self._observers:
            spectrum.subscribe(callback)

    def extend(self, spectra):
        for spectrum in spectra:
            self.append(spectrum)

    def remove(self, spectrum):
        idx = self.index(spectrum)
        self.emit("remove", spectrum=spectrum, index=idx)
        super().remove(spectrum)

    def clear(self):
        self.emit("clear")
        super().clear()

    def subscribe(self, callback):
        """Bind a new callback of class_ to this."""
        self._observers.append(callback)
        for spectrum in self:
            spectrum.subscribe(callback)

    def unsubscribe(self, callback):
        """Unbind the callback."""
        self._observers.remove(callback)
        for spectrum in self:
            spectrum.unsubscribe(callback)

    def emit(self, keyword, **kwargs):
        """Emits to all obervers."""
        for callback in self._observers:
            callback(keyword, self, **kwargs)
