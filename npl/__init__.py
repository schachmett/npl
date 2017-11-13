"""Loads the configuration ini and sets app name and version."""

import os
import configparser

__appname__ = "NPL"
__version__ = "0.1"
__authors__ = ["Simon Fischer <sfischer@ifp.uni-bremen.de>"]


BASEDIR = os.path.dirname(os.path.realpath(__file__))
# cfg_name = os.path.join(os.environ["HOME"], ".npl/config.ini")
CONFDIR = os.path.join(os.environ["HOME"], "projects/npl/.npl")
CFG_NAME = os.path.join(CONFDIR, "config.ini")

__config__ = configparser.ConfigParser()

if not os.path.isfile(CFG_NAME):
    if not os.path.isdir(os.path.dirname(CFG_NAME)):
        os.mkdir(os.path.dirname(CFG_NAME))
    __config__.add_section("general")
    __config__.set("general", "basedir", BASEDIR)
    __config__.set("general", "xydir", os.path.join(CONFDIR, "xy_temp"))
    __config__.set("general", "conf_filename", CFG_NAME)
    __config__.add_section("window")
    __config__.set("window", "xsize", "1200")
    __config__.set("window", "ysize", "700")
    __config__.add_section("io")
    __config__.set("io", "project_file", "None")

    with open(CFG_NAME, "w") as cfg_file:
        __config__.write(cfg_file)

__config__.read(CFG_NAME)
