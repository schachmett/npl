#!/usr/bin/python3.5
"""data containers"""

# import db_manager as dbm
import numpy as np


def main():
    """main stuff"""
    pass
#     dbh = dbm.DBHandler("test.db")
#     dbh.wipe_tables()
#     cont = SpectrumContainer(dbh)

#     parser = dbm.FileParser()
#     prs = list()
#     datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-01.xym"
#     prs.extend(parser.parse_spectrum_file(datafname))
#     datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-02.xym"
#     prs.extend(parser.parse_spectrum_file(datafname))
#     datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-03.xym"
#     prs.extend(parser.parse_spectrum_file(datafname))
#     for par in prs:
#         spec = Spectrum(par)
#         cont.append(spec)
#     cont.save_as("bla.npl")


class SpectrumContainer(list):
    """parses database for convenient use from the UI"""
#     to do: ID assignment
    def __init__(self, dbhandler):
        super().__init__()
        self.dbhandler = dbhandler

    def write_to_db(self):
        """writes self to database"""
        idlist = self.dbhandler.save_container(self)
        for i, sid in enumerate(idlist):
            self[i]["SpectrumID"] = sid

    def save_as(self, fname):
        """saves itself to database of name fname"""
        dbname = self.dbhandler.dbfilename
        self.dbhandler.change_dbfile(fname)
        self.write_to_db()
        self.dbhandler.change_dbfile(dbname)

    def show_only(self, spectrum_to_show):
        """sets all visibility values to None except for one"""
        for spectrum in self:
            if spectrum == spectrum_to_show:
                spectrum.plot()
            else:
                spectrum.unplot()

    def get_treeview_data(self):
        """gives database representation suitable for the treeview"""
        pass

    def get_plotter_data(self):
        """gives database representation suitable for the plootter"""
        pass


class Spectrum(dict):
    """stores spectrum data as an object"""
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
        if len(self["Name"]) == 0:
            self["Name"] = "(R {0})".format(self["EISRegion"])

    def plot(self):
        """switch plotting flag on"""
        self["Visibility"] = "default"

    def unplot(self):
        """switch plotting flag off"""
        self["Visibility"] = None

    def __eq__(self, other):
        """for testing equality"""
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


if __name__ == "__main__":
    main()
