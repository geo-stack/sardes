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


def _update_v2_to_v3(accessor: DatabaseAccessorSardesLite):
    """
    Update Sardes SQLite database schema to version 3 from version 2.
    """
    # Remove table 'pump_installation' because it is not used anymore.
    accessor.execute('DROP TABLE IF EXISTS pump_installation')
    accessor._session.flush()

    # Add the new tables that were  added in Sardes v0.13.0 for
    # the remarks and hydrogeochemistry.
    accessor.execute("DROP TABLE IF EXISTS remark")
    accessor.execute(
        """
        CREATE TABLE remark (
            remark_id INTEGER NOT NULL,
            sampling_feature_uuid CHAR(32),
            remark_type_id INTEGER,
            period_start DATETIME,
            period_end DATETIME,
            remark_text VARCHAR,
            remark_author VARCHAR(250),
            remark_date DATETIME,
            PRIMARY KEY (remark_id),
            FOREIGN KEY(sampling_feature_uuid) REFERENCES sampling_feature (sampling_feature_uuid),
            FOREIGN KEY(remark_type_id) REFERENCES remark_type (remark_type_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS remark_type")
    accessor.execute(
        """
        CREATE TABLE remark_type (
            remark_type_id INTEGER NOT NULL,
            remark_type_code VARCHAR(250),
            remark_type_name VARCHAR(250),
            remark_type_desc VARCHAR,
            PRIMARY KEY (remark_type_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS pump_types")
    accessor.execute(
        """
        CREATE TABLE pump_types (
            pump_type_id INTEGER NOT NULL,
            pump_type_name VARCHAR,
            pump_type_desc VARCHAR,
            PRIMARY KEY (pump_type_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS hg_params")
    accessor.execute(
        """
        CREATE TABLE hg_params (
            hg_param_id INTEGER NOT NULL,
            hg_param_code VARCHAR,
            hg_param_name VARCHAR,
            hg_param_regex VARCHAR,
            cas_registry_number VARCHAR,
            PRIMARY KEY (hg_param_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS hg_sampling_methods")
    accessor.execute(
        """
        CREATE TABLE hg_sampling_methods (
            hg_sampling_method_id INTEGER NOT NULL,
            hg_sampling_method_name VARCHAR,
            hg_sampling_method_desc VARCHAR,
            PRIMARY KEY (hg_sampling_method_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS purge")
    accessor.execute(
        """
        CREATE TABLE purge (
            purge_id INTEGER NOT NULL,
            hg_survey_id INTEGER,
            purge_sequence_no INTEGER,
            purge_seq_start DATETIME,
            purge_seq_end DATETIME,
            purge_outflow FLOAT,
            pump_type_id INTEGER,
            pumping_depth FLOAT,
            static_water_level FLOAT,
            PRIMARY KEY (purge_id),
            FOREIGN KEY(hg_survey_id) REFERENCES hg_surveys (hg_survey_id),
            FOREIGN KEY(pump_type_id) REFERENCES pump_types (pump_type_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS hg_surveys")
    accessor.execute(
        """
        CREATE TABLE hg_surveys (
            hg_survey_id INTEGER NOT NULL,
            sampling_feature_uuid CHAR(32),
            hg_survey_datetime DATETIME,
            hg_survey_depth FLOAT,
            hg_survey_operator VARCHAR,
            hg_sampling_method_id INTEGER,
            sample_filtered INTEGER,
            survey_note VARCHAR,
            PRIMARY KEY (hg_survey_id),
            FOREIGN KEY(sampling_feature_uuid) REFERENCES sampling_feature (sampling_feature_uuid),
            FOREIGN KEY(hg_sampling_method_id) REFERENCES hg_sampling_methods (hg_sampling_method_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS hg_param_values")
    accessor.execute(
        """
        CREATE TABLE hg_param_values (
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
            PRIMARY KEY (hg_param_value_id),
            FOREIGN KEY(hg_survey_id) REFERENCES hg_surveys (hg_survey_id),
            FOREIGN KEY(hg_param_id) REFERENCES hg_params (hg_param_id),
            FOREIGN KEY(meas_units_id) REFERENCES measurement_units (meas_units_id)
            )
        """
    )
    accessor.execute("DROP TABLE IF EXISTS measurement_units")
    accessor.execute(
        """
        CREATE TABLE measurement_units (
            meas_units_id INTEGER NOT NULL,
            meas_units_abb VARCHAR,
            meas_units_name VARCHAR,
            meas_units_desc VARCHAR,
            PRIMARY KEY (meas_units_id)
            )
        """
    )
    accessor._session.flush()

    # Delete all water quality reports saved as attachment from the database.
    accessor.execute(
        """
        DELETE FROM sampling_feature_attachment WHERE attachment_type = 2
        """
    )
    accessor._session.flush()
