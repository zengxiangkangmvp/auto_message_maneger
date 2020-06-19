from .builder import Builder, template, Row, make_html
from .color import parse_rules


class TablesBuilder(Builder):
    """
    {
        "describe": "多表格报表, 查询多个SQL并以表格展示在邮件正文中.",
        "info": [{"name":"title", "type": "text", "label": "标题", "des": "报表的标题"},
                 {"name":"excel", "type": "checkbox", "label": "附件", "des": "查询结果是否以excel附件形式一同发送"},
                 {"name":"name1","type": "text", "label": "表名称1", "des": "第一个SQL结果的名称"},
                 {"name":"SQL1", "type": "textarea", "label": "SQL", "des": "第一个SQL"},
                 {"name":"color1", "type": "textarea", "label": "颜色", "des": "每列的颜色设定"},
                 {"name":"name2","type": "text", "label": "表名称2", "des": "第二个SQL结果的名称"},
                 {"name":"SQL2", "type": "textarea", "label": "SQL", "des": "第二个SQL"},
                 {"name":"color2", "type": "textarea", "label": "颜色", "des": "每列的颜色设定"},
                 {"name":"name3","type": "text", "label": "表名称3", "des": "第三个SQL结果的名称"},
                 {"name":"SQL3", "type": "textarea", "label": "SQL", "des": "第三个SQL"},
                 {"name":"color3", "type": "textarea", "label": "颜色", "des": "每列的颜色设定"},
                 {"name":"name4","type": "text", "label": "表名称4", "des": "第四个SQL结果的名称"},
                 {"name":"SQL4", "type": "textarea", "label": "SQL", "des": "第四个SQL"},
                 {"name":"color4", "type": "textarea", "label": "颜色", "des": "每列的颜色设定"},
                 {"name":"name5","type": "text", "label": "表名称5", "des": "第五个SQL结果的名称"},
                 {"name":"SQL5", "type": "textarea", "label": "SQL", "des": "第五个SQL"},
                 {"name":"color5", "type": "textarea", "label": "颜色", "des": "每列的颜色设定"},
                 {"name":"comment", "type": "textarea", "label": "注释"}]
    }
    """

    def read_data(self):
        """
        读取数据并放入数据集合中
        """
        self.details = []
        for i in range(1, 6):
            name = self.info.get("name%d" % i, "表%d" % i)
            sql = self.info.get("SQL%d" % i, "")
            if sql == "":
                continue
            df = self.query(sql)
            rules = parse_rules(self["color%d" % i], df)
            self.details.append([name, df, rules])

    @property
    def with_excel(self):
        return self.info.get("excel", False)

    @property
    def df_attachments(self):
        if self.with_excel:
            k = self.info.get("attach_name", None) or self.msg_title
            k = "附表" if k == "" else k
            result = {k: self.details}
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
    def table_rows(self):
        """邮件主体: 实用 \n 分割的多行内容, 每行带一个标题和一个表"""
        rows = []
        for name, df, rules in self.details:
            table = make_html(df, rules)
            row = Row(name, table)
            rows.append(str(row))
        rows.append(self.comment_row)
        return "\n".join(rows)

    def make_html(self):
        html = template.format(title=self.report_title, rows=self.table_rows)
        return html
