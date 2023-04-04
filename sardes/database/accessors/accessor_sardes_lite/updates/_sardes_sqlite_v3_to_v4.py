# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Scripts to update the Sardes SQLite database schema.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sardes.database.accessors import DatabaseAccessorSardesLite
import pandas as pd


def _update_v3_to_v4(accessor: DatabaseAccessorSardesLite):
    """
    Update Sardes SQLite database schema to version 4 from version 3.

    Changelog:
    - Data in fields 'in_recharge_zone' and 'is_influenced' are now stored as
    integers instead of strings.
    - Renamed the field 'static_water_level' of table 'purge' to
    'water_level_drawdown'.
    """
    # Fetch data from the database.
    select_statement = (
        """
        SELECT sampling_feature_uuid, in_recharge_zone, is_influenced
        FROM sampling_feature_metadata;
        """
    )
    data = pd.read_sql_query(
        select_statement, accessor._session.connection(),
        index_col='sampling_feature_uuid'
        )

    # Delete and create new columns with the right type.
    accessor.execute(
        "ALTER TABLE sampling_feature_metadata DROP in_recharge_zone;"
    )
    accessor.execute(
        "ALTER TABLE sampling_feature_metadata ADD in_recharge_zone INTEGER;"
    )
    accessor.execute(
        "ALTER TABLE sampling_feature_metadata DROP is_influenced;"
    )
    accessor.execute(
        "ALTER TABLE sampling_feature_metadata ADD is_influenced INTEGER;"
    )

    # Transform 'in_recharge_zone' and 'is_influenced' data from str to Int64.
    int_map_dict = {'Oui': 1, 'oui': 1, 'Non': 0, 'non': 0, 'ND': 2, 'nd': 2}
    for column in ['in_recharge_zone', 'is_influenced']:
        data[column] = data[column].map(int_map_dict.get).astype('Int64')

    # Save the transformed data back in the database.
    for index, row in data.iterrows():
        accessor.execute(
            """
            UPDATE sampling_feature_metadata
            SET in_recharge_zone = :is_rechg, is_influenced = :is_inf
            WHERE sampling_feature_uuid = :uuid;
            """,
            params={'is_rechg': row['in_recharge_zone'],
                    'is_inf': row['is_influenced'],
                    'uuid': index}
        )

    # Rename column 'static_water_level' of table 'purge' to
    # 'water_level_drawdown'
    accessor.execute(
        "ALTER TABLE purge RENAME COLUMN static_water_level TO "
        "water_level_drawdown;"
    )
