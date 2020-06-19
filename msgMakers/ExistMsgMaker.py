from .MsgMaker import MsgMaker, pd


class ExistMsgMaker(MsgMaker):
    """查询某些数据是否存在, 如果存在则生成一条消息."""

    @staticmethod
    def inputs():
        inputs = [
            {"name": "sql", "type": "text", "label": "SQL", "des": "查询使用的SQL"},
            {"name": "title", "type": "text", "label": "提示主题", "des": "钉钉左侧消息预览中显示的文字"},
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

        top_n = df.iloc[: self.limit]
        text_array = []

        for i in top_n.columns:
            if "float" in top_n[i].dtype.name:
                top_n[i] = top_n[i].apply(lambda x: float_to_str(x)) + "&nbsp;"
            else:
                top_n[i] = top_n[i].fillna("-").astype(str) + "&nbsp;"

        text_array.append("| %s |" % " | ".join(top_n.columns.values + "&nbsp;"))
        text_array.append("| %s |" % " | ".join(["----" for c in top_n.columns]))
        for row in top_n.iloc:
            text_array.append("| %s |" % " | ".join(row))

        text = "  \n".join(text_array)
        title = self.info.get("title", "...")

        if title != "...":
            text = title + "  \n\n" + text

        if df.shape[0] > self.limit:
            text += "\n\n...等总计%d条" % df.shape[0]

        markdown = {"title": title, "text": text}
        result = {"msgtype": "markdown", "markdown": markdown}
        return result


def float_to_str(x, na_expr="-"):
    if pd.isna(x):
        return na_expr
    else:
        if int(x) == x:
            return str(int(x))
        else:
            return str(round(x, 2))
