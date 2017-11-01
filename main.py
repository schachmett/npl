#!/usr/bin/env python3
""" starts the program """

import sys
from npl import __config__
from npl.gui import Npl


def main():
    """ calls gui.py main function """
    app = Npl()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
