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
    - Renamed table 'purge' to 'purges'.
    - Added a new column 'purge_notes' to table 'purges'
    - Renamed the field 'static_water_level' of table 'purges' to
    'water_level_drawdown'.
    - Add a new table named 'hg_labs' to hold the list of labs that can
    analyze groundwater samples and replace column 'lab_name' by 'lab_id'
    in tables 'hg_param_values' with a foreign constaint to the
    new 'hg_labs' table.
    """

    # =========================================================================
    # Change data type of fields 'in_recharge_zone' and 'is_influenced'
    # from strings to integers.
    # =========================================================================

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
    int_map_dict = {'non': 0, 'no': 0, 'oui': 1, 'yes': 1, 'nd': 2, 'na': 2}
    for column in ['in_recharge_zone', 'is_influenced']:
        data[column] = data[column].str.lower()
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

    # =========================================================================
    # Rename table 'purge' to 'purges', add a new column 'purge_notes' and
    # rename column 'static_water_level' to 'water_level_drawdown'.
    # =========================================================================

    accessor.execute(
        "ALTER TABLE purge RENAME TO purges;"
    )
    accessor.execute(
        "ALTER TABLE purges ADD purge_notes;"
    )
    accessor.execute(
        "ALTER TABLE purges RENAME COLUMN static_water_level TO "
        "water_level_drawdown;"
    )

    # =========================================================================
    # Drop table 'pump_type' if it exists. The table used to hold that
    # information is named 'pump_types'. This table is an old relic that was
    # added during the first stages of the project.
    # =========================================================================
    accessor.execute("DROP TABLE IF EXISTS pump_type")

    # =========================================================================
    # Add new table 'hg_labs'.
    # =========================================================================

    accessor.execute("DROP TABLE IF EXISTS hg_labs")
    accessor.execute(
        """
        CREATE TABLE hg_labs (
            lab_id INTEGER NOT NULL,
            lab_code VARCHAR,
            lab_name VARCHAR,
            lab_contacts VARCHAR,
            PRIMARY KEY (lab_id)
            )
        """
    )

    # We cannot add a foreign key to table 'hg_labs' directly in the
    # existing table 'hg_param_values'. We need to create a completely new
    # table in order to do that.
    accessor.execute(
        """
        CREATE TABLE hg_param_values_new (
            hg_param_value_id INTEGER NOT NULL,
            hg_survey_id INTEGER,
            hg_param_id INTEGER,
            hg_param_value VARCHAR,
            lim_detection FLOAT,
            meas_units_id INTEGER,
            lab_sample_id VARCHAR,
            lab_name VARCHAR,
            lab_report_date DATETIME,
            method VARCHAR,
            notes VARCHAR,
            lab_id INTEGER,
            PRIMARY KEY (hg_param_value_id),
            FOREIGN KEY(hg_survey_id) REFERENCES hg_surveys (hg_survey_id),
            FOREIGN KEY(hg_param_id) REFERENCES hg_params (hg_param_id),
            FOREIGN KEY(meas_units_id) REFERENCES measurement_units (meas_units_id)
            FOREIGN KEY(lab_id) REFERENCES hg_labs (lab_id)
            )
        """
    )
    accessor.execute(
        "ALTER TABLE hg_param_values ADD lab_id INTEGER;"
    )
    accessor.execute(
        "INSERT INTO hg_param_values_new SELECT * FROM hg_param_values;"
    )
    accessor.execute(
        "DROP TABLE hg_param_values;"
    )
    accessor.execute(
        "ALTER TABLE hg_param_values_new RENAME TO hg_param_values;"
    )

    # Fetch the lab_names from table 'hg_param_values' and use it
    # to populate the 'hg_labs' table.
    lab_names = pd.read_sql_query(
        "SELECT hg_param_value_id, lab_name FROM hg_param_values;",
        accessor._session.connection(),
        index_col='hg_param_value_id'
        )

    lab_names_map = {}
    i = 0
    for lab_name in lab_names.lab_name.unique():
        if pd.isnull(lab_name):
            continue
        i += 1
        lab_names_map[lab_name] = i
        accessor.execute(
            """
            INSERT INTO hg_labs (lab_id, lab_code) VALUES (:lab_id, :lab_code);
            """,
            params={'lab_id': i, 'lab_code': lab_name}
        )

    # Populate the column 'lab_id' of table 'hg_param_values' and
    # drop the column 'lab_name'.
    for index, row in lab_names.iterrows():
        lab_name = row['lab_name']
        if lab_name not in lab_names_map:
            continue
        lab_id = lab_names_map[lab_name]
        accessor.execute(
            """
            UPDATE hg_param_values
            SET lab_id = :lab_id
            WHERE hg_param_value_id = :value_id;
            """,
            params={'lab_id': lab_id, 'value_id': index}
        )

    accessor.execute(
        "ALTER TABLE hg_param_values DROP lab_name;"
    )
