from .MsgMaker import MsgMaker


class FeedCardMsgMaker(MsgMaker):
    """查询某些数据是否存在, 如果存在则生成一条消息."""

    @staticmethod
    def inputs():
        inputs = [
            {
                "name": "sql",
                "type": "text",
                "label": "SQL",
                "des": "第一列:标题, 第二列:链接(可选), 第三列:图片(可选)",
            },
            {"name": "limit", "type": "text", "label": "条目限制", "des": "显示多少条数据"},
        ]
        return inputs

    @property
    def limit(self):
        return self.info.get("limit", 10)

    def make_msg(self):
        df = self.query(self.info["sql"])
        if df.shape[0] == 0:
            return {"empty": True}

        top_n = df.iloc[: self.limit].dropna()
        links = []

        for i in top_n.iloc:
            link = {"title": i[0]}
            if len(i) > 1:
                link["messageURL"] = i[1]
            if len(i) > 2:
                link["picURL"] = i[2]
            links.append(link)

        result = {"feedCard": {"links": links}, "msgtype": "feedCard"}
        return result
