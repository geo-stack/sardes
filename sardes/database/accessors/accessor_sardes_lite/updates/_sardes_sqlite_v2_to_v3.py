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


def _update_v2_to_v3(accessor):
    """
    Update Sardes SQLite database schema to version 3 from version 2.
    """
    # Remove the old tables 'pump_type' and 'pump_installation'.
    existing_table_names = accessor._get_table_names()
    if 'pump_type' not in existing_table_names:
        accessor.execute('DROP TABLE pump_type')
        accessor._session.flush()
    if 'pump_installation' not in existing_table_names:
        accessor.execute('DROP TABLE pump_installation')
        accessor._session.flush()

    # Add the new tables that were  added in Sardes v0.13.0 for
    # the remarks and hydrogeochemistry.
    existing_table_names = accessor._get_table_names()
    if 'remark' not in existing_table_names:
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
        accessor._session.flush()
    if 'remark_type' not in existing_table_names:
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
        accessor._session.flush()
    if 'hg_params' not in existing_table_names:
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
        accessor._session.flush()
    if 'hg_sampling_methods' not in existing_table_names:
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
        accessor._session.flush()
    if 'purge' not in existing_table_names:
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
        accessor._session.flush()
    if 'hg_surveys' not in existing_table_names:
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
        accessor._session.flush()
    if 'hg_param_values' not in existing_table_names:
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
        accessor._session.flush()
    if 'measurement_units' not in existing_table_names:
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
    accessor.execute("PRAGMA user_version = 3")
