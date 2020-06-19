from .MsgMaker import MsgMaker


class NotExistMsgMaker(MsgMaker):
    """不存在数据信息时则进行提示"""

    @staticmethod
    def inputs():
        inputs = [
            {"name": "sql", "type": "text", "label": "SQL", "des": "查询使用的SQL"},
            {"name": "msg", "type": "text", "label": "提示信息", "des": "机器人会提示的语句内容"},
        ]
        return inputs

    def make_msg(self):
        sql = self.info["sql"]
        if "LIMIT" not in sql.upper():
            sql = sql + " LIMIT 3"
        df = self.query(self.info["sql"])
        if df.shape[0] > 0:
            return {"empty": True}

        result = {"msgtype": "text", "text": {"content": self.info["msg"]}}

        return result
