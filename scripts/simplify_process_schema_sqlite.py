# -*- coding: utf-8 -*-
"""
A script to update the SQLite database schema for the changes made
in cgq-qgc/sardes#309
"""


from sardes.database.accessor_sardes_lite import (
    DatabaseAccessorSardesLite, Process, Base, SondeInstallation,
    PumpInstallation)

accessor = DatabaseAccessorSardesLite('D:/rsesq_test.db')

# %%
# Add 'sampling_feature_uuid' to 'process' table.

accessor.execute("ALTER TABLE process RENAME TO old_process;")
Base.metadata.create_all(accessor._engine, tables=[Process.__table__])
accessor._session.commit()
accessor.execute("INSERT INTO process (process_type, process_id) SELECT "
                 "process_type, process_id FROM old_process;")
accessor._session.commit()
accessor.execute("DROP TABLE old_process;")
accessor._session.commit()

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

accessor.execute(
    "ALTER TABLE sonde_installation RENAME TO old_sonde_installation;")
Base.metadata.create_all(
    accessor._engine, tables=[SondeInstallation.__table__])
accessor._session.commit()
accessor.execute(
    "INSERT INTO sonde_installation (install_uuid, sonde_uuid, start_date,"
    "end_date, install_depth, operator, install_note) SELECT "
    "install_uuid, sonde_uuid, start_date, end_date, install_depth, "
    "operator, install_note FROM old_sonde_installation;")

sonde_installations = accessor._session.query(SondeInstallation)
for sonde_installation in sonde_installations:
    process_id = accessor.execute(
        "SELECT process_installation.process_id "
        "FROM sonde_installation, process_installation "
        "WHERE process_installation.install_uuid=:uuid;",
        uuid=str(sonde_installation.install_uuid).replace('-', '')
        ).fetchone().process_id
    sonde_installation.process_id = process_id
accessor._session.commit()

accessor._session.commit()
accessor.execute("DROP TABLE old_sonde_installation;")
accessor._session.commit()

# %%
# Remove 'sampling_feature_uuid' from 'pump_installation' and add 'process_id'.

accessor.execute(
    "ALTER TABLE pump_installation RENAME TO old_pump_installation;")
Base.metadata.create_all(
    accessor._engine, tables=[PumpInstallation.__table__])
accessor._session.commit()
accessor.execute(
    "INSERT INTO pump_installation (install_uuid, pump_type_id, start_date,"
    "end_date, install_depth, operator, install_note) SELECT "
    "install_uuid, pump_type_id, start_date, end_date, install_depth, "
    "operator, install_note FROM old_pump_installation;")

pump_installations = accessor._session.query(PumpInstallation)
for pump_installation in pump_installations:
    process_id = accessor.execute(
        "SELECT process_installation.process_id FROM process_installation "
        "WHERE process_installation.install_uuid=:uuid;",
        uuid=str(pump_installation.install_uuid).replace('-', '')
        ).fetchone().process_id
    pump_installation.process_id = process_id
accessor._session.commit()

accessor._session.commit()
accessor.execute("DROP TABLE old_pump_installation;")
accessor._session.commit()

# %%
# Drop table 'process_installation'

accessor._session.commit()
accessor.execute("DROP TABLE process_installation;")
accessor._session.commit()

accessor.close_connection()
