# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard imports
import json
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_config_dir
import psycopg2

# ---- Local imports
from sardes import __appname__


class DBConnectionWorker(object):


class PostgreSqlPresenter(object):

    def __init__(self):
        super(PostgreSqlPresenter, self).__init__()
        self.conn = None
        self.connect_to_db()

    def get_dbconfig(self):
        filename = osp.join(get_config_dir(__appname__), 'dbconfig.json')
        with open(filename) as json_file:
            dbconfig = json.load(json_file)
        return dbconfig

    def connect_to_db(self):
        dbconfig = self.get_dbconfig()
        self.conn = psycopg2.connect(' '.join(
            ["{}='{}'".format(key, value) for key, value in dbconfig.items()]
            ))



if __name__ == "__main__":
    PostgreSqlPresenter()
    # def connect(self):
    #     conn = psycopg2.connect(
    #         "dbname='rsesq' user='rsesq' host='198.73.161.237' password='((Rsesq2019'")




