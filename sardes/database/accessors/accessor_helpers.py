# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd


def init_tseries_edits():
    """
    Init and return an empty multiindex pandas dataframe that can be
    used to edit timeseries data in the database with
    :func:`DatabaseAccessor.save_timeseries_data_edits`.
    """
    tseries_edits = pd.DataFrame(
        [], columns=['datetime', 'obs_id', 'data_type', 'value'])
    tseries_edits.set_index(
        'datetime', inplace=True, drop=True)
    tseries_edits.set_index(
        'obs_id', inplace=True, drop=True, append=True)
    tseries_edits.set_index(
        'data_type', inplace=True, drop=True, append=True)
    return tseries_edits


def init_tseries_dels():
    """
    Init and return an empty pandas dataframe that can be
    used to delete timeseries data from the database with
    :func:`DatabaseAccessor.delete_timeseries_data`.
    """
    return pd.DataFrame([], columns=['obs_id', 'datetime', 'data_type'])


def create_empty_readings(data_types):
    """
    Create an empty pandas dataframe specifically formatted to hold
    groundwater monitoring data.

    Parameters
    ----------
    data_types : list of DataType
        The list of data types that are going to be saved in this dataframe.

    Returns
    -------
    dataframe : DataFrame
        A correctly formatted dataframe to hold grounwater monitoring data.

    """
    dataframe = pd.DataFrame(
        [],
        columns=(['datetime', 'sonde_id'] +
                 data_types +
                 ['install_depth', 'obs_id']))

    # Make sure the columns have the right dtype.
    dataframe['datetime'] = pd.to_datetime(dataframe['datetime'])
    for data_type in data_types:
        dataframe[data_type] = dataframe[data_type].astype(float)
    dataframe['install_depth'] = dataframe['install_depth'].astype(float)
    dataframe['obs_id'] = dataframe['obs_id'].astype(pd.Int64Dtype())

    return dataframe


if __name__ == "__main__":
    from sardes.api.timeseries import DataType
    data_types = [DataType.WaterLevel, DataType.WaterTemp, DataType.WaterEC]
    empty_readings = create_empty_readings(data_types)
    print(empty_readings)
    print(empty_readings.dtypes)
