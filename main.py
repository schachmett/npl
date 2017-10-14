#!/usr/bin/env python3
""" starts the program """

import sys
from npl import __config__
from npl.gui import Npl


def main():
    """ calls gui.py main function """
    app = Npl()

    if __config__.get("io", "project_file") != "None":
        try:
            app.open_silently(__config__.get("io", "project_file"))
        except FileNotFoundError:
            print("file '{}' not found".format(
                __config__.get("io", "project_file")))
            __config__.set("io", "project_file", "None")

    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
