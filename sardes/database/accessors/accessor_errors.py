# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Third party imports

# ---- Local imports
from sardes.config.locale import _


class SardesVersionError(Exception):
    """
    Exception raised when the version of Sardes is outdated
    compared to the version of the database.

    Parameters
    ----------
    req_version : int
        The maximum database version supported by the current version of
        Sardes.
    """

    def __init__(self, req_version: int):
        self.message = _(
            "Your Sardes application is outdated and does not support "
            "databases whose version is higher than {}. Please "
            "update Sardes and try again."
            ).format(req_version)
        super().__init__(self.message)


class DatabaseVersionError(Exception):
    """
    Exception raised when the version of the database is outdated
    compared to the version of Sardes.

    Parameters
    ----------
    cur_version : int
        The current version of the database.
    req_version : int
        The required version of the database.
    """

    def __init__(self, cur_version: int, req_version: int):
        self.message = _(
            "The version of this database is {} and is outdated. "
            "Please update your database to version {} and try again."
            ).format(cur_version, req_version)
        super().__init__(self.message)
