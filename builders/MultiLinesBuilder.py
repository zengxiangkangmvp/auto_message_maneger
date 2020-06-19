from .builder import pd, Builder, template
import json
import matplotlib.pyplot as plt


class MultiLinesBuilder(Builder):
    """
    {
        "describe": "使用不同条件并以折线图形式绘制结果的报表.",
        "info": [{"name":"title", "type": "text", "label": "标题", "des": "报表的标题"},
                 {"name":"groupCol", "type": "text", "label": "Group by", "des": "Group by 的列或者表达式"},
                 {"name":"aggrCol", "type": "text", "label": "聚合函数", "des": "Group by 使用的函数"},
                 {"name":"having", "type": "text", "label": "Having", "des": "Having 筛选条件"},
                 {"name":"cumsum", "type": "checkbox", "label": "累加", "des": "最终显示的值是否累加."},
                 {"name":"fillna", "type": "checkbox", "label": "填充NA", "des": "是否将 na 值填充为0.", "default": true},
                 {"name":"showRate", "type": "checkbox", "label": "显示比例", "des": "显示结果的数值,不勾选则显示比率."},
                 {"name":"showLoc", "type": "text", "label": "关键行", "des": "在图表下方显示哪些行的数值,以JSON表示,\\n例如1,3,15,30天发货率可以填写[1,3,15,30]"},
                 {"name":"item1", "type": "text", "label": "条件1", "des": "图例1 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item2", "type": "text", "label": "条件2", "des": "图例2 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item3", "type": "text", "label": "条件3", "des": "图例3 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item4", "type": "text", "label": "条件4", "des": "图例4 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item5", "type": "text", "label": "条件5", "des": "图例5 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item6", "type": "text", "label": "条件6", "des": "图例6 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item7", "type": "text", "label": "条件7", "des": "图例7 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item8", "type": "text", "label": "条件8", "des": "图例8 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item9", "type": "text", "label": "条件9", "des": "图例9 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"item10", "type": "text", "label": "条件10", "des": "图例10 的信息, 使用 名称<空格>where 来表示\\n例:SZ01 left(仓库,2)='SZ'"},
                 {"name":"comment", "type": "textarea", "label": "注释"}]
    }
    """

    def parse_alias(self, col):
        """返回列的别称"""
        i = col.upper().rfind(" AS ")
        alias = col if i == -1 else col[i + 4 :]
        if alias[0] == "`" and alias[-1] == "`":
            alias = alias[1:-1]
        return alias

    def parse_expr(self, col):
        """返回列的计算部分"""
        i = col.upper().rfind(" AS ")
        expr = ("`%s`" % col) if i == -1 else col[:i]
        return expr

    def name(self, i):
        """返回 ITEM 中例如 SZ left(仓库号,2) ='SZ' 中的 "SZ" """
        key = "item%s" % str(i)
        index = self[key].strip().find(" ")
        if index == -1:
            return self[key].strip()
        else:
            return self[key].strip()[:index]

    def where(self, i):
        """返回 ITEM 中例如 SZ left(仓库号,2) ='SZ' 中的 left(仓库号,2) ='SZ' """
        key = "item%s" % str(i)
        index = self[key].strip().find(" ")
        if index == -1:
            return "1=1"
        else:
            return self[key].strip()[index + 1 :]

    def make_sql(self, i):
        """根据 item 的索引生成 SQL"""
        group_expr = self.parse_expr(self["groupCol"])
        group_alias = self.parse_alias(self["groupCol"])
        aggrCol = self.parse_expr(self["aggrCol"])
        table = self["table"]
        name = self.name(i)
        where = self.where(i)
        sql = (
            f"SELECT {group_expr} as `{group_alias}`, \n"
            f"       {aggrCol} as `{name}` \n"
            f"  FROM `{table}` \n"
            f" WHERE {where} \n"
            f" GROUP BY {group_expr} \n"
        )

        having = self["having"]
        if having is not None and having != "":
            sql += f"HAVING {having}"

        return sql

    def read_data(self):
        """
        对于提供了 SQL 的信息读取数据, 添加到 dataset 列表中

        这里会遍历 item1 到 item10
        对于填写了内容的每个 item 查询生成一个 df
        然后根据 df 的 index 对所有 df 进行全外连接生成连接的表
        根据是否需要进行 fillna 进行 fill 操作

        最后将连接的 df, 和解释各列的 df 作为实例的属性
        """
        dataset = []
        explain = []
        for i in range(1, 11):
            item = self["item%d" % i]
            if item is not None and item != "":
                explain.append(item)
                sql = self.make_sql(i)
                group_alias = self.parse_alias(self["groupCol"])
                df = self.query(sql, index=group_alias)
                dataset.append(df)
            else:
                continue

        df = dataset[0]
        for i in range(1, len(dataset)):
            how = dict(left_index=True, right_index=True, how="outer")
            df = pd.merge(df, dataset[i], **how)

        self.df = df
        self.df_explain = pd.DataFrame({"各图例条件说明": explain})

    @property
    def title(self):
        return self.info.get("title", "未命名报表")

    @property
    def msg_title(self):
        return self.title

    @property
    def df_display(self):
        """
        用于展示的 df, 根据设置会进行显示比例,累积求和,填充0值的操作
        """
        df = self.df.copy()
        if self["showRate"] is True:
            df = df / df.sum()
        if self["cumsum"] is True:
            df = df.cumsum().fillna(method="ffill")
        if self["fillna"] is True:
            df = df.fillna(0)
        return df

    @property
    def figures(self):
        plt.clf()
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        df = self.df_display
        df.plot()
        if self["showRate"] is True:
            plt.ylim((0, 1.05))
        plt.grid()
        plt.tight_layout()
        return {"chart1": plt}

    @property
    def df_attachments(self):
        """附件excel, 会有两个工作表, 数据是查询结果, 说明是每一列的条件"""
        k = self.info.get("attach_name", None) or self.title
        dfs = [["数据", self.df], ["说明", self.df_explain]]
        return {k: dfs}

    def make_html(self):
        body = '<tr><td><img src="cid:chart1" alt="图表" /></tr><td>'
        if self["showLoc"] is not None:
            locs = json.loads(self["showLoc"])
            df = self.df_display.reindex(locs)
            if self["showRate"] is True:
                for col in df.columns:
                    df[col] = df[col].apply(lambda x: "%.2f%%" % (x * 100))
            table = df.to_html(na_rep="")
            _old = 'class="dataframe"'
            _new = 'class="dataframe" style="border-collapse:collapse"'
            table = table.replace(_old, _new)
            body += "<tr><td>%s</td></tr>" % table
            body += self.comment_row
        html = template.format(title=self.title, rows=body)
        return html
