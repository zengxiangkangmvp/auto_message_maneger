import sqlalchemy
import pandas as pd
import json
from os import environ

DB_INFO_PATH = r"\documents\gkbjy\dbs.json"
ACCOUNT = "mysql"


class MsgMaker(object):
    def __init__(self, info):
        self.connstr = self.get_connstr(info)
        self.info = info

    @staticmethod
    def inputs():
        """用于页面输入的控件"""
        return []

    def assert_before_make(self):
        sql = self.info.get("testSql")
        if sql is None or str(sql).strip() == "":
            return
        df = self.query(sql)
        assert df.shape[0] > 0, "发送消息前的检验未通过."
        assert df.all().all(), "发送消息前的检验未通过."

    def get_connstr(self, info):
        """根据传入info的信息生成连接字符串"""
        path = environ["USERPROFILE"] + DB_INFO_PATH
        db = self.read_json(path)[ACCOUNT]
        schema = info.get("database", "")
        t = (db["user"], db["pwd"], db["server"], schema)
        return "mysql+pymysql://%s:%s@%s/%s" % t

    def read_json(self, path):
        fp = open(path, encoding="utf-8")
        result = json.load(fp)
        fp.close()
        return result

    def query(self, sql):
        eng = sqlalchemy.create_engine(self.connstr)
        sql = sql.replace(r"%", r"%%")
        result = pd.read_sql(sql, eng)
        eng.dispose()
        return result

    def make_msg(self):
        raise NotImplementedError()
