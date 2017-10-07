"""manages database file"""

import sqlite3
import re
import os
import pickle
import numpy as np
from npl.containers import Spectrum, SpectrumContainer

BASEDIR = "/home/simon/npl/.npl"
XYDIR = os.path.join(BASEDIR, "xyfiles")


class FileParser():
    """Parses arbitrary spectrum files"""
    def __init__(self):
        pass

    def parse_spectrum_file(self, fname):
        """finds out file extension and calls appropriate parsing function"""
        parseds = list()
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
        data = dict()
        data["Filename"] = fname
        values = np.loadtxt(data["Filename"], delimiter="\t", comments="L",
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
        data["Visibility"] = None
        data["Name"] = str()
        if header[3][0] is not "1":
            return None
        else:
            return data

    def unpack_eistxt(self, fname):
        """splits Omicron EIS txt file"""
        
        splitregex = re.compile(r"^Region.*")
        skipregex = re.compile(r"^[0-9]*\s*False\s*0\).*")
        fnamelist = []
        splitcount = 0
        with open(fname, "r") as eisfile:
            for line in eisfile:
                if re.match(splitregex, line):
                    splitcount += 1
                    wname = "{0}/{1}-{2}.xym".format(XYDIR,
                                                     os.path.basename(fname),
                                                     str(splitcount).zfill(2))
                    xyfile = open(wname, 'w')
                    fnamelist.append(wname)
                    skip = False
                elif re.match(skipregex, line):
                    skip = True
                elif splitcount == 0:
                    raise TypeError("wrong file, not matching EIS format")
                if not skip:
                    xyfile.write(line)
        return fnamelist


class DBHandler():
    """ handles basic database accessing """
    spectrum_keys = ["Name", "Notes", "EISRegion", "Filename", "Sweeps",
                     "DwellTime", "PassEnergy", "Visibility"]

    def __init__(self, dbfilename="npl.db"):
        self.dbfilename = os.path.join(BASEDIR, dbfilename)

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
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            for sql in create_sql:
                table_name = sql.split()[2]
                cursor.execute("SELECT name FROM sqlite_master WHERE name=?",
                               (table_name, ))
                exists = cursor.fetchall()
                if not exists:
                    cursor.execute(sql, ())
                    database.commit()

    def wipe_tables(self):
        """drops em hard"""
        with sqlite3.connect(self.dbfilename) as database:
            sqls = ["DROP TABLE IF EXISTS Spectrum",
                    "DROP TABLE IF EXISTS SpectrumData"]
            cursor = database.cursor()
            for sql in sqls:
                cursor.execute(sql, ())
            database.commit()
        self.create_tables()

    def get_container(self):
        """loads text project file to current db"""
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            sql = """SELECT SpectrumID, Name, Notes, EISRegion, Filename,
                     Sweeps, DwellTime, PassEnergy, Visibility
                     FROM Spectrum"""
            spectrum_container = SpectrumContainer()
            cursor.execute(sql, ())
            spectra = cursor.fetchall()
            for spectrum in spectra:
                sid = spectrum[0]
                sql = """SELECT Energy, Intensity, Type
                         FROM SpectrumData
                         WHERE SpectrumID=?"""
                cursor.execute(sql, (sid, ))
                spectrum_data = cursor.fetchall()[0]
                specdict = {"SpectrumID": sid, "Name": spectrum[1],
                            "Notes": spectrum[2], "EISRegion": spectrum[3],
                            "Filename": spectrum[4], "Sweeps": spectrum[5],
                            "DwellTime": spectrum[6],
                            "PassEnergy": spectrum[7],
                            "Visibility": spectrum[8]}
                if spectrum_data[2] == "default":
                    specdict["Energy"] = pickle.loads(spectrum_data[0])
                    specdict["Intensity"] = pickle.loads(spectrum_data[1])
                spectrum_container.append(Spectrum(specdict))
        return spectrum_container

    def save_container(self, spectrum_container):
        """dumps current db as project text file"""
        self.wipe_tables()
        idlist = list()
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            for spectrum in spectrum_container:
                idlist.append(self.add_spectrum(spectrum, cursor))
            database.commit()
        return idlist

    def change_dbfile(self, new_filename):
        """change db filename"""
        self.dbfilename = new_filename

    def remove_dbfile(self):
        """trashes db file"""
        os.remove(self.dbfilename)
        self.dbfilename = None

    def add_spectrum(self, spectrum, cursor=None):
        """adds new spectrum from a dict from the parser"""
        needs_closing = False
        if cursor is None:
            needs_closing = True
            database = sqlite3.connect(self.dbfilename)
            cursor = database.cursor()
        sql = """INSERT INTO Spectrum(Name, Notes, EISRegion, Filename,
                                      Sweeps, DwellTime, PassEnergy,
                                      Visibility)
                 VALUES(?, ?, ?, ?, ?, ?, ?, ?)"""
        values = tuple(spectrum[key] for key in self.spectrum_keys)
        cursor.execute(sql, values)
        spectrum_id = cursor.lastrowid
        sql = """INSERT INTO SpectrumData(Energy, Intensity, Type,
                                          SpectrumID)
                VALUES(?, ?, ?, ?)"""
        energy = pickle.dumps(spectrum["Energy"])
        intensity = pickle.dumps(spectrum["Intensity"])
        cursor.execute(sql, (energy, intensity, "default", spectrum_id))
        if needs_closing:
            database.commit()
            database.close()
        return spectrum_id

    def remove_spectrum(self, spectrum_id):
        """removes spectrum"""
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            sql = "DELETE FROM Spectrum WHERE SpectrumID=?"
            cursor.execute(sql, (spectrum_id, ))
            sql = "DELETE FROM SpectrumData WHERE SpectrumID=?"
            cursor.execute(sql, (spectrum_id, ))
            database.commit()

    def amend_spectrum(self, spectrum_id, newspectrum):
        """alters spectrum"""
        self.remove_spectrum(spectrum_id)
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            sql = """INSERT INTO Spectrum(Name, Notes, EISRegion, Filename,
                                          Sweeps, DwellTime, PassEnergy,
                                          Visibility, SpectrumID)
                     VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            values = (*[newspectrum[key] for key in self.spectrum_keys],
                      spectrum_id)
            cursor.execute(sql, values)
            spectrum_id = cursor.lastrowid

            sql = """INSERT INTO SpectrumData(Energy, Intensity, Type,
                                              SpectrumID)
                     VALUES(?, ?, ?, ?)"""
            energy = pickle.dumps(newspectrum["Energy"])
            intensity = pickle.dumps(newspectrum["Intensity"])
            cursor.execute(sql, (energy, intensity, "default", spectrum_id))
            database.commit()

    def sid(self, spectrum):
        """searches for a spectrum and gives the ID"""
        with sqlite3.connect(self.dbfilename) as database:
            cursor = database.cursor()
            sql = """SELECT SpectrumID FROM Spectrum
                     WHERE Notes=? AND EISRegion=? AND Filename=? AND Sweeps=?
                     AND DwellTime=? AND PassEnergy=?"""
            values = tuple(spectrum[key] for key in self.spectrum_keys[1:-1])
            cursor.execute(sql, values)
            ids = cursor.fetchall()
            if len(ids) < 1:
                print("Did not find {0}".format(spectrum))
                return None
            if len(ids) == 1:
                return ids[0][0]
            if len(ids) > 1:
                print("Found multiple IDs for spectrum {0}:\n"
                      "{1}".format(spectrum, ids))
                return ids[0][0]


class RSFHandler():
    """ handles rsf library business """
    def __init__(self, filename):
        self.filename = filename
        self.color = 0
        self.colors = "grcmy"
        self.elements = []
        self.source = ""

    def get_element(self, element, source):
        """ gets binding energies, rsf and orbital name for specific
        element """
        self.elements.append(element.title())
        if self.source == "":
            self.source = source
        elif self.source != source:
            print("multiple sources requested from RSFHandler!")

        with sqlite3.connect(self.filename) as rsfbase:
            cursor = rsfbase.cursor()
            sql = """SELECT Fullname, IsAuger, BE, RSF FROM Peak
                     WHERE Element=? AND (Source=? OR Source=?)"""
            values = (element.title(), source, "Any")
            cursor.execute(sql, values)
            rsf_data = cursor.fetchall()
            rsf_dicts = []
            for dataset in rsf_data:
                auger_bool = dataset[1] == 1.0
                rsf_dicts.append({"Fullname": dataset[0], "IsAuger": auger_bool,
                                  "BE": dataset[2], "RSF": dataset[3],
                                  "color": self.colors[self.color]})
            self.color += 1
            if self.color >= len(self.colors): self.color = 0
            return rsf_dicts

    def reset(self):
        self.color = 0
        self.elements = []
        self.source = ""
