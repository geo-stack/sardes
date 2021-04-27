# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the MIT License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd


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
