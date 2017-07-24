#!/usr/bin/python3.5
"""manages database file"""

import sqlite3
import re
import os
import pickle
import numpy as np

BASEDIR = "/home/simon/npl/"
SETTINGS_FOLDER = os.path.join(BASEDIR, ".npl/")
SETTINGS_FILE = SETTINGS_FOLDER + "/settings.json"


def main():
    """does stuff, mainly for testing now"""
    dbh = DBHandler("test.db")
    dbh.create_tables()

    parser = FileParser()
    datafname = "/home/simon/npl/.npl/Au111-cleaning.txt-01.xym"
    parsed = parser.parse_spectrum_file(datafname)
    for data in parsed:
        dbh.add_spectrum(data)
    dbh.remove_spectrum(3)


class FileParser():
    """Parses arbitrary spectrum files"""
    def __init__(self):
        pass

    def parse_spectrum_file(self, fname):
        """finds out file extension and calls appropriate parsing function"""
        parseds = []
        if fname.split(".")[-1] == "xym":
            parsed = self.parse_xymfile(fname)
            parseds.append(parsed)
        elif fname.split(".")[-1] == "txt":
            xymfiles = self.unpack_eistxt(fname)
            for xymfile in xymfiles:
                parsed = self.parse_xymfile(xymfile)
                parseds.append(parsed)
        elif fname.split(".")[-1] == "xy":
            print("parsing {} not yet implemented".format(fname))
        else:
            print("file {} not recognized".format(fname))
        return parseds

    def read_rsf_file(self):
        """parses rsf library"""
        pass

    def parse_xymfile(self, fname):
        """parses Omicron split txt file"""
        data = {}
        data["Filename"] = fname
        values = np.loadtxt(data["Filename"], delimiter="\t",
                            skiprows=5, unpack=True)
        data["Energy"] = values[0, ::-1]
        data["Intensity"] = values[1, ::-1]
        with open(data["Filename"], "r") as xyfile:
            header = [x.split("\t") for i, x in enumerate(xyfile)
                      if i in range(0, 4)]
        data["EISRegion"] = int(header[1][0])
        data["Sweeps"] = int(header[1][6])
        data["DwellTime"] = float(header[1][7])
        data["PassEnergy"] = float(header[1][9])
        data["Notes"] = header[1][12]
        data["Visibility"] = "default"
        data["Name"] = str()
        if header[3][0] is not "1":
            return None
        else:
            return data

    def unpack_eistxt(self, fname):
        """splits Omicron EIS txt file"""
        splitregex = re.compile("^Region.*")
        splitcounter = 0
        with open(fname, "r") as eisfile:
            wname = "{0}{1}-{2}.xym".format(SETTINGS_FOLDER,
                                            os.path.basename(fname),
                                            str(splitcounter).zfill(2))
            xyfile = open(wname, 'w')
            for line in eisfile:
                if re.match(splitregex, line):
                    splitcounter += 1
                    wname = "{0}{1}-{2}.xym".format(SETTINGS_FOLDER,
                                                    os.path.basename(fname),
                                                    str(splitcounter).zfill(2))
                    print(wname)
                    xyfile = open(wname, 'w')
                xyfile.write(line)
        fnamelist = []
        for i in range(0, splitcounter+1):
            xym_fname = "{0}{1}-{2}.xym".format(SETTINGS_FOLDER,
                                                os.path.basename(fname),
                                                str(i).zfill(2))
            if os.stat(xym_fname).st_size != 0:
                fnamelist.append(xym_fname)
        return fnamelist


class DBHandler():
    """handles basic database accessing"""
    spectrum_keys = ["Name", "Notes", "EISRegion", "Filename", "Sweeps",
                     "DwellTime", "PassEnergy", "Visibility"]

    def __init__(self, dbfilename):
        self.dbfilename = dbfilename

    def query(self, sql, parameters):
        """queries db"""
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            cursor.execute(sql, parameters)
            result = cursor.fetchall()
        return result

    def execute(self, sql, parameters):
        """executes sql command"""
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            cursor.execute(sql, parameters)
            lastid = cursor.lastrowid
            database.commit()
        return lastid

    def create_tables(self):
        """creates table via sql command if not already created"""
        create_sql = ["""CREATE TABLE Spectrum
                         (SpectrumID integer,
                          Name text,
                          Notes text,
                          EISRegion integer,
                          Filename text,
                          Sweeps integer,
                          DwellTime real,
                          PassEnergy real,
                          Visibility text,
                          PRIMARY KEY (SpectrumID))""",
                      """CREATE TABLE SpectrumData
                         (SpectrumDataID integer,
                          Energy blob,
                          Intensity blob,
                          Type text,
                          SpectrumID integer,
                          PRIMARY KEY (SpectrumDataID),
                          FOREIGN KEY (SpectrumID) REFERENCES
                                       Spectrum(SpectrumID))"""]
        for sql in create_sql:
            table_name = sql.split()[2]
            exists = self.query("SELECT name FROM sqlite_master WHERE name=?",
                                (table_name, ))
            if exists:
                print("Table '{0}' already exists, did not create it "
                      "again".format(table_name))
            else:
                self.execute(sql, ())

    def drop_tables(self):
        """drops em hard"""
        sql = """DROP TABLE Spectrum
                 DROP TABLE SpectrumData"""
        self.execute(sql, ())

    def get_container(self):
        """loads text project file to current db"""
        sql = """SELECT SpectrumID, Name, Notes, EISRegion, Filename, Sweeps,
                 DwellTime, PassEnergy, Visibility
                 FROM Spectrum"""
        spectrum_container = []
        spectra = self.query(sql, ())
        for spectrum in spectra:
            sid = spectrum[0]
            sql= """SELECT Energy, Intensity, Type
                    FROM SpectrumData
                    WHERE SpectrumID=?"""
            spectrum_data = self.query(sql, (sid, ))
            specdict = {"SpectrumID": sid, "Name": spectrum[1],
                        "Notes": spectrum[2], "EISRegion": spectrum[3],
                        "Filename": spectrum[4], "Sweeps": spectrum[5],
                        "DwellTime": spectrum[6], "PassEnergy": spectrum[7],
                        "Visibility": spectrum[8]}
            if spectrum_data[2] == "default":
                specdict["Energy"] = pickle.loads(spectrum_data[0])
                specdict["Intensity"] = pickle.loads(spectrum_data[1])
            spectrum_container.append(Spectrum(specdict))
        return spectrum_container

    def save_container(self, spectrum_container):
        """dumps current db as project text file"""
        self.drop_tables()
        for spectrum in spectrum_container:
            self.add_spectrum(spectrum)

    def change_dbfile(self, new_filename):
        self.dbfilename = new_filename

    def add_spectrum(self, spectrum):
        """adds new spectrum from a dict from the parser"""
        sql = """INSERT INTO Spectrum(Name, Notes, EISRegion, Filename, Sweeps,
                                      DwellTime, PassEnergy, Visibility)
                 VALUES(?, ?, ?, ?, ?, ?, ?, ?)"""
        values = tuple(spectrum[key] for key in self.spectrum_keys)
        spectrum_id = self.execute(sql, values)

        sql = """INSERT INTO SpectrumData(Energy, Intensity, Type, SpectrumID)
                VALUES(?, ?, ?, ?)"""
        energy = pickle.dumps(spectrum["Energy"])
        intensity = pickle.dumps(spectrum["Intensity"])
        self.execute(sql, (energy, intensity, "default", spectrum_id))
        return spectrum_id

    def remove_spectrum(self, spectrum_id):
        """removes spectrum"""
        sql = "DELETE FROM Spectrum WHERE SpectrumID=?"
        self.execute(sql, (spectrum_id, ))
        sql = "DELETE FROM SpectrumData WHERE SpectrumID=?"
        self.execute(sql, (spectrum_id, ))

    def amend_spectrum(self, spectrum_id, newspectrum):
        """alters spectrum"""
        self.remove_spectrum(spectrum_id)
        sql = """INSERT INTO Spectrum(Name, Notes, EISRegion, Filename, Sweeps,
                                      DwellTime, PassEnergy, Visibility,
                                      SpectrumID)
                 VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        values = (*[newspectrum[key] for key in self.spectrum_keys],
                  spectrum_id)
        spectrum_id = self.execute(sql, values)

        sql = """INSERT INTO SpectrumData(Energy, Intensity, Type, SpectrumID)
                VALUES(?, ?, ?, ?)"""
        energy = pickle.dumps(newspectrum["Energy"])
        intensity = pickle.dumps(newspectrum["Intensity"])
        self.execute(sql, (energy, intensity, "default", spectrum_id))

    def sid(self, spectrum):
        """searches for a spectrum and gives the ID"""
        sql = """SELECT SpectrumID FROM Spectrum
                 WHERE Notes=? AND EISRegion=? AND Filename=? AND Sweeps=?
                 AND DwellTime=? AND PassEnergy=?"""
        values = (newspectrum[key] for key in self.spectrum_keys[:-1])
        ids = self.query(sql, values)
        if len(ids) < 1:
            print("Did not find {}".format(spectrum))
            return None
        if len(ids) == 1:
            return ids
        if len(ids) > 1:
            print("Found multiple IDs for spectrum {0}: "
                  "{1}".format(spectrum, ids))
            return None


class SpectrumContainer():
    """parses database for convenient use from the UI"""
    def __init__(self, dbhandler):
        pass

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
    defaulting_dict = {"ID": None, "Visibility": False}

    def __init__(self, datadict):
        super().__init__()
        for key in self.essential_keys:
            if key not in datadict.keys():
                raise ValueError
            else:
                self[key] = datadict[key]
        for key in self.defaulting_dict.keys():
            if key not in datadict.keys():
                self[key] = self.defaulting_dict[key]
            else:
                self[key] = datadict[key]

#     def __setitem__(self, key, value):
#         self[key] = value
#         if self["ID"] is not None:
#             self.dbh.amend(self["ID"], self)
#         else:
#             self.dbh.add_spectrum(self)

    def plot(self):
        """switch plotting flag on"""
        self["Visibility"] = True

    def unplot(self):
        """switch plotting flag off"""
        self["Visibility"] = False


if __name__ == "__main__":
    main()
#                    """CREATE TABLE Region
#                       (RegionID integer,
#                        SpectrumDataID integer,
#                        PRIMARY KEY (RegionID),
#                        FOREIGN KEY (SpectrumDataID) REFERENCES
#                                    SpectrumData(SpectrumDataID))""",
#                    """CREATE TABLE Peak
#                       (PeakID integer,
#                        RegionID integer,
#                        RSFID integer,
#                        PRIMARY KEY (PeakID),
#                        FOREIGN KEY (RegionID) REFERENCES Region(RegionID),
#                        FOREIGN KEY (RSFID) REFERENCES RSF(RSFID))""",
#                    """CREATE TABLE RSF
#                       (RSFID integer,
#                       PRIMARY KEY (RSFID))"""]
