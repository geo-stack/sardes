# -*- coding: utf-8 -*-
"""
A script to update the SQLite database schema for the changes made
in cgq-qgc/sardes#309
"""


import sqlite3
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import sqlite
from sardes.database.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, Process, SondeInstallation, PumpInstallation)


# DATABASE = 'D:/rsesq_test.db'
DATABASE = 'D:/rsesq_prod.db'
# DATABASE = 'D:/rsesq_prod_sample.db'
accessor = DatabaseAccessorSardesLite(DATABASE)


# %%
# Add 'sampling_feature_uuid' to 'process' table.

# We need to do this enabled legacy_alter_table and disabled foreign_keys
# for the connection or else, the foreign keys of parent tables will
# reference the renamed table.
# https://www.sqlite.org/lang_altertable.html
# https://stackoverflow.com/questions/4897867
# See cgq-qgc/sardes#310.

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys=OFF;")
conn.execute("PRAGMA legacy_alter_table=ON;")
conn.execute("BEGIN TRANSACTION;")
conn.execute("ALTER TABLE process RENAME TO old_process;")
conn.execute(CreateTable(Process.__table__)
             .compile(dialect=sqlite.dialect()).string)
conn.execute("INSERT INTO process (process_type, process_id) SELECT "
             "process_type, process_id FROM old_process;")
conn.execute("DROP TABLE old_process;")
conn.execute("COMMIT;")
conn.close()

# %%
# Copy 'sampling_feature_uuid' from 'sonde_installation' to 'process'.

processes = accessor._session.query(Process)
for process in processes:
    if process.process_type == 'sonde installation':
        sampling_feature_uuid = accessor.execute(
            "SELECT sonde_installation.sampling_feature_uuid "
            "FROM sonde_installation, process_installation "
            "WHERE process_installation.process_id=:id AND "
            "sonde_installation.install_uuid="
            "process_installation.install_uuid;",
            id=process.process_id
            ).fetchone().sampling_feature_uuid
        process.sampling_feature_uuid = sampling_feature_uuid
accessor._session.commit()

# %%
# Remove 'sampling_feature_uuid' from 'sonde_installation' and
# add 'process_id'.

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys=OFF;")
conn.execute("PRAGMA legacy_alter_table=ON;")
conn.execute("BEGIN TRANSACTION;")
conn.execute(
    "ALTER TABLE sonde_installation RENAME TO old_sonde_installation;")
conn.execute(CreateTable(SondeInstallation.__table__)
             .compile(dialect=sqlite.dialect()).string)
conn.execute(
    "INSERT INTO sonde_installation (install_uuid, sonde_uuid, start_date,"
    "end_date, install_depth, operator, install_note) SELECT "
    "install_uuid, sonde_uuid, start_date, end_date, install_depth, "
    "operator, install_note FROM old_sonde_installation;")
conn.execute("DROP TABLE old_sonde_installation;")
conn.execute("COMMIT;")
conn.close()

sonde_installations = accessor._session.query(SondeInstallation)
for sonde_installation in sonde_installations:
    process_id = accessor.execute(
        "SELECT process_installation.process_id "
        "FROM sonde_installation, process_installation "
        "WHERE process_installation.install_uuid=:uuid;",
        uuid=str(sonde_installation.install_uuid).replace('-', '')
        ).fetchone().process_id
    sonde_installation.process_id = process_id

# %%
# Remove 'sampling_feature_uuid' from 'pump_installation' and add 'process_id'.

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys=OFF;")
conn.execute("PRAGMA legacy_alter_table=ON;")
conn.execute("BEGIN TRANSACTION;")
conn.execute("ALTER TABLE pump_installation RENAME TO old_pump_installation;")
conn.execute(CreateTable(PumpInstallation.__table__)
             .compile(dialect=sqlite.dialect()).string)
conn.execute(
    "INSERT INTO pump_installation (install_uuid, pump_type_id, start_date,"
    "end_date, install_depth, operator, install_note) SELECT "
    "install_uuid, pump_type_id, start_date, end_date, install_depth, "
    "operator, install_note FROM old_pump_installation;")
conn.execute("DROP TABLE old_pump_installation;")
conn.execute("COMMIT;")
conn.close()

pump_installations = accessor._session.query(PumpInstallation)
for pump_installation in pump_installations:
    process_id = accessor.execute(
        "SELECT process_installation.process_id FROM process_installation "
        "WHERE process_installation.install_uuid=:uuid;",
        uuid=str(pump_installation.install_uuid).replace('-', '')
        ).fetchone().process_id
    pump_installation.process_id = process_id
accessor._session.commit()


# %%
# Drop table 'process_installation'

accessor.execute("DROP TABLE process_installation;")
accessor._session.commit()

accessor.close_connection()
