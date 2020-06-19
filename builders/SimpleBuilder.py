from .builder import Builder, template, make_html, parse_rules


class SimpleBuilder(Builder):
    """
    {
        "describe": "简单报表, 如果查询到数据则发送一份表格, 没有查询到数据则不发送.",
        "info": [{"name":"title", "type": "text", "label": "标题", "des": "报表的标题"},
                 {"name":"SQL", "type": "textarea", "label": "SQL", "des": "查询结果的SQL"},
                 {"name":"colorRule", "type": "textarea", "label": "颜色格式", "des": "每列的颜色设定"},
                 {"name":"excel", "type": "checkbox", "label": "附件", "des": "查询结果是否以excel附件形式一同发送"},
                 {"name":"other1name", "type": "text", "label": "明细1名称", "des": "附件中明细1的工作表名称"},
                 {"name":"other1sql", "type": "textarea", "label": "明细1SQL", "des": "附件中明细工作表1的数据SQL"},
                 {"name":"other1color", "type": "textarea", "label": "明细1颜色", "des": "每列的颜色设定"},
                 {"name":"other2name", "type": "text", "label": "明细2名称", "des": "附件中明细2的工作表名称"},
                 {"name":"other2sql", "type": "textarea", "label": "明细2SQL", "des": "附件中明细工作表2的数据SQL"},
                 {"name":"other2color", "type": "textarea", "label": "明细2颜色", "des": "每列的颜色设定"},
                 {"name":"other3name", "type": "text", "label": "明细3名称", "des": "附件中明细3的工作表名称"},
                 {"name":"other3sql", "type": "textarea", "label": "明细3SQL", "des": "附件中明细工作表3的数据SQL"},
                 {"name":"other3color", "type": "textarea", "label": "明细3颜色", "des": "每列的颜色设定"},
                 {"name":"other4name", "type": "text", "label": "明细4名称", "des": "附件中明细4的工作表名称"},
                 {"name":"other4sql", "type": "textarea", "label": "明细4SQL", "des": "附件中明细工作表4的数据SQL"},
                 {"name":"other4color", "type": "textarea", "label": "明细4颜色", "des": "每列的颜色设定"},
                 {"name":"other5name", "type": "text", "label": "明细5名称", "des": "附件中明细5的工作表名称"},
                 {"name":"other5sql", "type": "textarea", "label": "明细5SQL", "des": "附件中明细工作表5的数据SQL"},
                 {"name":"other5color", "type": "textarea", "label": "明细5颜色", "des": "每列的颜色设定"},
                 {"name":"comment", "type": "textarea", "label": "注释"}]
    }
    """

    def read_data(self):
        sql = self.make_sql()
        self.df = self.query(sql)
        self.details = []
        for i in range(1, 6):
            name = "other%dname" % i
            sql = "other%dsql" % i
            name = self.info.get(name, "detail%d" % i)
            sql = self.info.get(sql, "")
            if sql == "":
                continue
            df = self.query(sql)
            color_rules = "other%dcolor" % i
            color_rules = parse_rules(self[color_rules], df)
            self.details.append([name, df, color_rules])

    def make_sql(self):
        return self["SQL"]

    def color_rules(self, i):
        if i == "main":
            return parse_rules(self["colorRule"], self.df)

    @property
    def with_excel(self):
        return self.info.get("excel", False)

    @property
    def df_attachments(self):
        if self.with_excel:
            k = self.info.get("attach_name", None) or self.msg_title
            k = "附表" if k == "" else k
            dfs = [["main", self.df, self.color_rules("main")]]
            dfs.extend(self.details)
            result = {k: dfs}
            return result
        else:
            return {}

    @property
    def msg_title(self):
        return self.report_title

    @property
    def report_title(self):
        return self.info.get("title", "")

    @property
    def need_post(self):
        return self.df.shape[0] > 0

    def make_html(self):
        color_rules = self.color_rules("main")
        html = make_html(self.df, color_rules)
        body = f"<tr><td>{html}</td></tr>"
        body += self.comment_row
        html = template.format(title=self.report_title, rows=body)
        return html
