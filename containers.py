#!/usr/bin/python3.5
"""data containers"""

import db_manager as dbm
import numpy as np

def main():
    dbh = dbm.DBHandler("test.db")
    dbh.wipe_tables()
    cont = SpectrumContainer(dbh)

    parser = dbm.FileParser()
    prs = list()
    datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-01.xym"
    prs.extend(parser.parse_spectrum_file(datafname))
    datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-02.xym"
    prs.extend(parser.parse_spectrum_file(datafname))
    datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-03.xym"
    prs.extend(parser.parse_spectrum_file(datafname))
    for par in prs:
        sp = Spectrum(par)
        cont.append(sp)
    print(cont[0:3])


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
        dbname = self.dbh.dbfilename
        self.dbh.change_dbfile(fname)
        self.write_to_db()
        self.dbh.change_dbfile(dbname)

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
    defaulting_dict = {"SpectrumID": None, "Visibility": False}

    def __init__(self, datadict):
        super().__init__()
        for key in self.essential_keys:
            if key not in datadict:
                raise ValueError("missing key for Spectrum"
                                 "init: {}".format(key))
            else:
                self[key] = datadict[key]
        for key in self.defaulting_dict:
            if key not in datadict:
                self[key] = self.defaulting_dict[key]
            else:
                self[key] = datadict[key]

    def plot(self):
        """switch plotting flag on"""
        self["Visibility"] = True

    def unplot(self):
        """switch plotting flag off"""
        self["Visibility"] = False


if __name__ == "__main__":
    main()
