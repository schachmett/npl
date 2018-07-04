"""Provides a Spectrum class that stores all spectrum relevant data and
metadata. Also provides SpectrumContainer, a list containing Spectrums
and providing callback connection for changing Spectrums."""

import uuid
import re

import numpy as np

from npl.processing import (
    calculate_background, moving_average, get_energy_at_maximum,
    normalize, RegionFitModelIface)


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

        for attr in ("energy", "intensity"):
            if attr not in kwargs:
                raise ValueError("Missing property {}".format(attr))

        self._observers = []
        self.sid = int(uuid.uuid4()) & (1<<64)-1
        self._energy = kwargs["energy"]
        self.energy = self._energy
        self._intensity = kwargs["intensity"]
        self.intensity = self._intensity
        self.regions = []

        self.regionname = 0

        for (attr, default) in self._defaults.items():
            setattr(self, attr, kwargs.get(attr, default))

        if not self.name and self.eis_region:
            self.name = "(R {})".format(self.eis_region)

    def set(self, **kwargs):
        """Change values that alter the spectrum."""
        calibration = kwargs.get("calibration", None)
        smoothness = kwargs.get("smoothness", None)
        norm = kwargs.get("norm", None)

        if calibration is not None and calibration != self.calibration:
            self.calibration = calibration
            self.energy = self._energy + self.calibration
        if (smoothness is not None and smoothness != self.smoothness
                or norm is not None and norm != self.norm):
            intensity = self._intensity
            if norm is not None:
                self.norm = norm
            if smoothness is not None:
                self.smoothness = smoothness
            intensity = normalize(intensity, self.norm)
            intensity = moving_average(intensity, self.smoothness)
            self.intensity = intensity

        for region in self.regions:
            region.set(spectrum_changed=True)

        self.emit("changed_spectrum", **kwargs)

    def get_energy_at_maximum(self, span):
        """Returns the energy at the intensity maximum in a given energy
        span=(emin, emax)."""
        maxen = get_energy_at_maximum(self.energy, self.intensity, span)
        return maxen

    def plot(self):
        """Switch plotting flag on. b: plot background, d: plot spectrum
        (-> default), r: plot region markers"""
        self.visibility += "bdrp"

    def unplot(self):
        """Switch plotting flags off."""
        self.visibility = ""

    def add_region(self, **kwargs):
        """Adds a region to self.regions."""
        region = Region(**kwargs, spectrum=self)
        self.regions.append(region)
        self.emit("add_region", region=region)
        for callback in self._observers:
            region.subscribe(callback)

    def remove_region(self, region):
        """Removes a region from self.regions."""
        self.regions.remove(region)
        self.emit("remove_region", region=region)

    def clear_regions(self):
        """Removes all regions from self.regions."""
        self.regions.clear()
        self.emit("remove_region", region=None)

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

    def __eq__(self, other):
        """For testing equality."""
        if self.sid == other.sid:
            return True
        return False

    @staticmethod
    def title(attr):
        """Returns the user friendly string for an attribute."""
        if attr in Spectrum.titles:
            return Spectrum.titles[attr]
        return attr


class Region(object):
    """A region is a part of a spectrum."""
    # pylint: disable=too-many-instance-attributes
    bgtypes = ("none", "shirley", "linear")
    peaknames = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, **kwargs):
        super().__init__()

        for attr in ("spectrum", "emin", "emax"):
            if attr not in kwargs:
                raise TypeError("Missing property {}".format(attr))

        self._observers = []
        self.sid = int(uuid.uuid4()) & (1<<64)-1
        self.spectrum = kwargs["spectrum"]
        self.emin = None    # these 5 will be set during self.set
        self.emax = None
        self.bgtype = None
        self.energy = None
        self.intensity = None
        self.background = None

        self.peakname = 0

        self.set(bgtype="shirley", emin=kwargs["emin"], emax=kwargs["emax"])

        self.peaks = []
        self.model = RegionFitModelIface(self)
        self.fit_all = None

        self.name = kwargs.get(
            "name", "Region {}".format(self.spectrum.regionname + 1))
        self.spectrum.regionname += 1

    def set(self, **kwargs):
        """Change values that alter the Region: emin, emax, bgtype, energy,
        intensity and background (last three indirectly)."""
        emin = kwargs.get("emin", None)
        emax = kwargs.get("emax", None)
        bgtype = kwargs.get("bgtype", None)

        spectrum_changed = kwargs.get("spectrum_changed", False)

        if (emin is not None and emin != self.emin
                or emax is not None and emax != self.emax
                or spectrum_changed):
            if emin is not None:
                self.emin = emin
            if emax is not None:
                self.emax = emax
            idx1, idx2 = sorted([
                np.searchsorted(self.spectrum.energy, self.emin),
                np.searchsorted(self.spectrum.energy, self.emax)])
            self.energy = self.spectrum.energy[idx1:idx2]
            self.intensity = self.spectrum.intensity[idx1:idx2]
            # two times check for bgtype because calculate_background
            # has to be executed either way
            if bgtype is not None and bgtype != self.bgtype:
                self.bgtype = bgtype
            self.background = calculate_background(
                self.bgtype, self.energy, self.intensity)
        # even if emin, emax stay the same, background has to be recalculated
        # in these cases:
        elif bgtype is not None and bgtype != self.bgtype:
            self.bgtype = bgtype
            self.background = calculate_background(
                self.bgtype, self.energy, self.intensity)

        self.emit("changed_region", **kwargs)

    def background_from_energy(self, energy):
        """Returns background intensity at specified energy."""
        index = (np.abs(self.energy - energy)).argmin()
        return self.background[index]

    def fit(self):
        """Do the fit and store the intensities."""
        self.model.fit()
        self.emit("fit")

    @property
    def fit_intensity(self):
        """Fetches the evaluation of the total model from ModelIface."""
        return self.model.get_intensity()

    def add_peak(self, **kwargs):
        """Adds a peak and guesses the parameters."""
        peak = Peak(region=self, **kwargs)
        self.peaks.append(peak)
        self.model.add_peak(peak)
        self.emit("add_peak")
        for observer in self._observers:
            peak.subscribe(observer)

    def remove_peak(self, peak):
        """Removes a peak from self.peaks."""
        self.peaks.remove(peak)
        self.model.remove_peak(peak)
        self.emit("remove_peak")

    def clear_peaks(self):
        """Removes all peaks from this region."""
        self.peaks.clear()
        self.emit("remove_peak")

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


class Peak(object):
    """This object fits a peak in the real spectrum and is defined as part of
    a Region."""
    # pylint: disable=access-member-before-definition, no-member
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=too-many-instance-attributes
    _defaults = {
        "name": "",
        "region": None,
        "spectrum": None,
        "model_name": "PseudoVoigt",
        "area": None,
        "center": None,
        "fwhm": None,
        "params": None,
        "guess": False}
    def __init__(self, **kwargs):
        self._observers = []
        for attr in ("region",):
            if attr not in kwargs:
                raise TypeError("Missing property {}".format(attr))

        self.sid = int(uuid.uuid4()) & (1<<64)-1
        self.region = kwargs["region"]
        for (attr, default) in self._defaults.items():
            setattr(self, attr, kwargs.get(attr, default))
        if not self.name:
            self.name = self.region.peaknames[self.region.peakname]
            self.region.peakname += 1

        self.prefix = "p{}_".format(self.sid)
        if self.spectrum is None:
            self.spectrum = self.region.spectrum

        if "height" in kwargs and "area" not in kwargs and "fwhm" in kwargs:
            self.area = (kwargs["height"]
                         * (kwargs["fwhm"] * np.sqrt(np.pi / np.log(2)))
                         / (1 + np.sqrt(1 / (np.pi * np.log(2)))))

        self.model = self.region.model
        self.model.add_peak(self)
        if self.guess:
            self.model.guess_params(self)
        else:
            self.model.init_params(
                self, fwhm=self.fwhm, area=self.area, center=self.center)

    def set(self, **kwargs):
        """The setter ensures notifying the observers."""
        self.fwhm = kwargs.get("fwhm", self.fwhm)
        self.area = kwargs.get("area", self.area)
        self.center = kwargs.get("center", self.center)
        if any([attr in kwargs for attr in ["fwhm", "area", "center"]]):
            self.model.init_params(
                self, fwhm=self.fwhm, area=self.area, center=self.center)
        self.emit("changed_peak")

    @property
    def fit_intensity(self):
        """Fetches peak intensity from the ModelIface."""
        return self.model.get_peak_intensity(self)

    def set_constraints(self, attr, **kwargs):
        """Sets a constraint for peak fitting."""
        self.model.add_constraint(self, attr, **kwargs)

    def get_constraint(self, attr, argname):
        """Sets a relation between fitting parameters."""
        return self.model.get_constraint(self, attr, argname)

    def set_model_func(self, model_name):
        """Sets the fitting model."""
        self.model.remove_peak(self)
        self.model_name = model_name
        self.model.add_peak(self)
        if self.guess:
            self.model.guess_params(self)
        else:
            self.model.init_params(
                self, area=self.area, fwhm=self.fwhm, center=self.center)

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
                return idx
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
        self.emit("add_spectrum", spectrum=spectrum, index=idx)
        for callback in self._observers:
            spectrum.subscribe(callback)

    def extend(self, spectra):
        for spectrum in spectra:
            self.append(spectrum)

    def remove(self, spectrum):
        idx = self.index(spectrum)
        self.emit("remove_spectrum", spectrum=spectrum, index=idx)
        super().remove(spectrum)

    def clear(self):
        self.show_only([])
        self.emit("clear_container")
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
