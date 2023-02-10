# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.config.locale import _


class SardesVersionError(Exception):
    """
    Exception that should be raised when the version of Sardes is outdated
    compared to the version of the database.

    Parameters
    ----------
    req_version : int
        The maximum database version supported by the current version of
        Sardes.
    """

    def __init__(self, req_version: int):
        self.req_version = req_version
        self.message = _(
            "Your Sardes application is outdated and does not support "
            "databases whose version is higher than {}. Please "
            "update Sardes and try again."
            ).format(req_version)
        super().__init__(self.message)


class DatabaseVersionError(Exception):
    """
    Exception that should be raised when the version of the database is
    outdated compared to the version of Sardes.

    Parameters
    ----------
    cur_version : int
        The current version of the database.
    req_version : int
        The required version of the database.
    """

    def __init__(self, cur_version: int, req_version: int):
        self.cur_version = cur_version
        self.req_version = req_version
        self.message = _(
            "The version of this database is {} and is outdated. "
            "Please update your database to version&nbsp;{} and try "
            "to connect again."
            ).format(cur_version, req_version)
        super().__init__(self.message)


class DatabaseUpdateError(Exception):
    """
    Exception that should be raised when a database update failed.

    Parameters
    ----------
    from_version : int
        The version from which the database was updated.
    to_version : int
        The version of the database at which the update failed.
    exception: Exeption:
        The original exception that was catched when updating the database.
    """

    def __init__(self, from_version: int, to_version: int,
                 exception: Exception):
        self.from_version = from_version
        self.to_version = to_version
        self.exception = exception
        self.message = _(
            "Failed to update the database from version {} to {} : {}"
            ).format(from_version, to_version, exception)
        super().__init__(self.message)
