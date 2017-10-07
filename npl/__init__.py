import os
import configparser
import io

__appname__ = "NPL"
__version__ = "0.1"
__authors__ = ["Simon Fischer <sfischer@ifp.uni-bremen.de>"]


basedir = os.path.dirname(os.path.realpath(__file__))
# cfg_name = os.path.join(os.environ["HOME"], ".npl/config.ini")
cfg_name = os.path.join(os.environ["HOME"], "npl/.npl/config.ini")

if not os.path.isfile(cfg_name):
    __config__ = configparser.ConfigParser()
    __config__.add_section("general")
    __config__.set("general", "basedir", basedir)
    __config__.set("general", "conf_filename", cfg_name)
    __config__.add_section("window")
    __config__.set("window", "xsize", "1200")
    __config__.set("window", "ysize", "700")
    __config__.add_section("io")
    __config__.set("io", "project_file", "None")

    with open(cfg_name, "w") as cfg_file:
        __config__.write(cfg_file)

__config__ = configparser.ConfigParser()
__config__.read(cfg_name)
