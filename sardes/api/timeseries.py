# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
from collections.abc import Mapping
from enum import Enum

# ---- Third party imports
from pandas import DatetimeIndex, DataFrame
import numpy as np

# ---- Local imports
from sardes.config.locale import _


class DataType(Enum):
    """
    This enum type describes the type of data constituing the time series.
    """
    WaterLevel = (0, 'blue', _("Water level"), _("Water Level"))
    WaterTemp = (1, 'red', _("Water temperature"), _("Temperature"))
    WaterEC = (2, 'cyan', _("Water electrical conductivity"),
               _("Conductivity"))

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _: int, color: str, title: str, label: str):
        self._color = color
        self._title = title
        self._label = label

    @property
    def color(self):
        return self._color

    @property
    def title(self):
        return self._title

    @property
    def label(self):
        return self._label


class TimeSeriesGroup(Mapping):
    """
    Sardes time series group class.

    The :class:`TimeSeriesGroup` class provides an abstract container to
    manage sardes :class:`TimeSeries` that belongs to the same monitored
    property.

    Parameters
    ----------
    data_type: DataType
        The type of data constituing the time series that are contained in
        this group.
    prop_name: str
        The common human readable name describing the data constituing
        the time series that are contained in this group.
    prop_units: str
        The units in which the data are saved.
    yaxis_inverted: bool
        A boolean to indicate whether the data should be plotted on an
        inverted y-axis (positive towards bottom).
    """

    def __init__(self, data_type, prop_name, prop_units,
                 yaxis_inverted=False):
        self._timeseries = []
        self.data_type = DataType(data_type)
        self.prop_name = prop_name
        self.prop_units = prop_units
        self.yaxis_inverted = yaxis_inverted

    def __len__(self, key):
        return len(self._tseries)

    def __setitem__(self, key, value):
        return NotImplementedError

    def __getitem__(self, key):
        return NotImplementedError

    def __iter__(self):
        for tseries in self._timeseries:
            yield tseries

    def __str__(self):
        return self.get_merged_timeseries().__str__()

    # ---- Timeseries
    @property
    def timeseries(self):
        """
        Return a list of timeseries associated with this monitored property.
        """
        return self._timeseries

    def add_timeseries(self, tseries):
        """
        Add a new timeseries to this monitored property.
        """
        self._timeseries.append(tseries)

    # ---- Utilities
    def get_merged_timeseries(self):
        """
        Return a pandas dataframe containing the data from all the timeseries
        that were added to this group.
        """
        if len(self.timeseries) >= 1:
            merged_tseries = self.timeseries[0]._data.to_frame()
            merged_tseries.columns = [self.data_type]
            # Add series ID to the dataframe.
            merged_tseries['obs_id'] = self.timeseries[0].id
            # Add sonde ID to the dataframe.
            merged_tseries['sonde_id'] = self.timeseries[0].sonde_id
            # Add datetime to the dataframe.
            merged_tseries['datetime'] = merged_tseries.index
            # Reset index, but preserve the datetime data.
            merged_tseries.reset_index(drop=True, inplace=True)

            # Append or merge the remaining timeseries with the first one.
            for tseries in self.timeseries[1:]:
                tseries_to_append = tseries._data.to_frame()
                tseries_to_append.columns = [self.data_type]
                tseries_to_append['obs_id'] = tseries.id
                tseries_to_append['sonde_id'] = tseries.sonde_id
                tseries_to_append['datetime'] = tseries_to_append.index
                tseries_to_append.reset_index(drop=True, inplace=True)
                merged_tseries = merged_tseries.append(
                    tseries_to_append, ignore_index=True,
                    verify_integrity=True, sort=True)
        elif len(self.timeseries) == 0:
            merged_tseries = DataFrame([])
        return merged_tseries

    # ---- Data selection
    def clear_selected_data(self):
        """
        Clear all selected data in the timeseries of this timeseries group.
        """
        for tseries in self._timeseries:
            tseries.clear_selected_data()

    def select_data(self, *args, **kargs):
        """
        This is a convenience method to select data in the timeseries of this
        group for a given period and range of values.
        """
        for tseries in self._timeseries:
            tseries.select_data(*args, **kargs)


class TimeSeries(Mapping):
    """
    Sardes time series class.

    Attributes
    ----------
    data
        A pandas Series with datetime indexes.
    tseries_id
        A unique ID used to reference this time series between Sardes GUI and
        the database by the database accessor.
    tseries_name: str
        A common human readable name used to reference this time series in the
        GUI and the graphs.
    tseries_units: str
        The units of the data this timeseries is referencing to.
    sonde_id
        An ID used to reference the sonde with which the data of this time
        series were acquired.
    """

    def __init__(self, data, tseries_id, tseries_name=None,
                 tseries_units=None, tseries_color=None,
                 sonde_id=None):
        super().__init__()
        self._data = data
        self.name = tseries_name
        self.id = tseries_id
        self.units = tseries_units
        self.color = tseries_color
        self.sonde_id = sonde_id

        self._undo_stack = []
        self._selected_data_indexes = DatetimeIndex([])

    def __len__(self, key):
        return len(self._data)

    def __setitem__(self, key, value):
        return NotImplementedError

    def __getitem__(self, key):
        return NotImplementedError

    def __iter__(self):
        return NotImplementedError

    def __str__(self):
        return self._data.__str__()

    # ---- Attributes
    @property
    def data(self):
        return self._data

    @property
    def dates(self):
        return self._data.index.values

    @property
    def strftime(self):
        return self._data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    # ---- Data Selection
    def select_data(self, xrange=None, yrange=None):
        """
        Select data for a given period and range of values.

        Return a pandas DatetimeIndex containing the datetime indexes
        of the timeseries corresponding to the data in the specified
        period and range of values.

        The resulting datetime indexes are also added to a list of
        already selected indexes, whose corresponding data can be obtained
        with the get_selected_data method.

        Parameters
        ----------
        xrange: tuple of datetime
            A tuple of 2-datetime objects specifying the start and end of
            a period.
        yrange: tuple of float
            A tuple of 2-floats specifying a range of values.

        Returns
        -------
        pandas.DatetimeIndex
            A pandas datetime index corresponding to the data in the
            specified period and range of values.
        """
        if xrange is not None and self._data.index.tzinfo is None:
            # Make sure the datetime objects or the specified period
            # use the same timezone info as that of the timeseries.
            xrange = (xrange[0].replace(tzinfo=self._data.index.tzinfo),
                      xrange[1].replace(tzinfo=self._data.index.tzinfo))

        if xrange and yrange:
            indexes = (
                self._data[(self._data.index >= xrange[0]) &
                           (self._data.index <= xrange[1]) &
                           (self._data >= yrange[0]) &
                           (self._data <= yrange[1])
                           ]).index
        elif xrange:
            indexes = (
                self._data[(self._data.index >= xrange[0]) &
                           (self._data.index <= xrange[1])
                           ]).index
        elif yrange:
            indexes = (
                self._data[(self._data >= yrange[0]) &
                           (self._data <= yrange[1])
                           ]).index
        else:
            indexes = DatetimeIndex([])

        self._selected_data_indexes = (
            self._selected_data_indexes.append(indexes))

        return indexes

    def get_selected_data(self):
        """
        Get the previously selected data of this timeseries.

        Return a pandas Series containing the data of this timeseries that
        were previously selected by the user.
        """
        return self._data.loc[self._selected_data_indexes]

    def clear_selected_data(self):
        """
        Clear the previously selected data of this timeseries.

        Clear the data of this timeseries that were previously selected
        by the user.
        """
        self._selected_data_indexes = DatetimeIndex([])

    # ---- Versionning
    @property
    def has_uncommited_changes(self):
        """"
        Return whether there is uncommited changes to the water level data.
        """
        return bool(len(self._undo_stack))

    def commit(self):
        """Commit the changes made to the water level data to the project."""
        raise NotImplementedError

    def undo(self):
        """Undo the last changes made to the water level data."""
        if self.has_uncommited_changes:
            changes = self._undo_stack.pop(-1)
            self._data[changes.index] = changes

    def clear_all_changes(self):
        """
        Clear all changes that were made to the water level data since the
        last commit.
        """
        while self.has_uncommited_changes:
            self.undo()

    def delete_waterlevels_at(self, indexes):
        """Delete the water level data at the specified indexes."""
        if len(indexes):
            self._add_to_undo_stack(indexes)
            self._data.iloc[indexes] = np.nan

    def _add_to_undo_stack(self, indexes):
        """
        Store the old water level values at the specified indexes in a stack
        before changing or deleting them. This allow to undo or cancel any
        changes made to the water level data before commiting them.
        """
        if len(indexes):
            self._undo_stack.append(self._data.iloc[indexes, 0].copy())


# =============================================================================
# ---- Utilities
# =============================================================================
def merge_timeseries_groups(tseries_groups):
    """
    Merge the time data contained in multiple timeseries groups in a single
    dataframe.
    """
    dataf = None
    for tseries_group in tseries_groups:
        if tseries_group is None:
            continue
        tseries = tseries_group.get_merged_timeseries()
        if tseries.empty:
            continue
        if dataf is None:
            dataf = tseries
        else:
            dataf = dataf.merge(
                tseries,
                left_on=['datetime', 'obs_id', 'sonde_id'],
                right_on=['datetime', 'obs_id', 'sonde_id'],
                how='outer', sort=True)

    # Reorder the columns so that the data are displayed nicely.
    grp_names = [grp.data_type for grp in tseries_groups if
                 grp.data_type in dataf.columns]
    dataf = dataf[['datetime', 'sonde_id'] + grp_names + ['obs_id']]

    return dataf


if __name__ == '__main__':
    print(DataType.WaterLevel)
    print(DataType.WaterLevel.value)
    print(DataType.WaterLevel.name)
    print(DataType.WaterLevel.color)
    print(DataType.WaterLevel.label)
