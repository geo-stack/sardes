# -*- coding: utf-8 -*-
"""
A script to fix the forieng keys of the 'sampling_feature' table in the
SQLite database.

See cgq-qgc/sardes#310.
"""


import sqlite3
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import sqlite
from sardes.database.accessor_sardes_lite import SamplingFeature


DATABASE = 'D:/rsesq_test.db'
# DATABASE = 'D:/rsesq_prod.db'
# DATABASE = 'D:/rsesq_prod_sample.db'

conn = sqlite3.connect(DATABASE)
conn.execute("PRAGMA foreign_keys=OFF;")
conn.execute("PRAGMA legacy_alter_table=ON;")
conn.execute("BEGIN TRANSACTION;")
conn.execute("ALTER TABLE sampling_feature RENAME TO old_sampling_feature;")
conn.execute(CreateTable(SamplingFeature.__table__)
             .compile(dialect=sqlite.dialect()).string)
conn.execute(
    "INSERT INTO sampling_feature SELECT * FROM old_sampling_feature;")
conn.execute("DROP TABLE old_sampling_feature;")
conn.execute("COMMIT;")
conn.close()
