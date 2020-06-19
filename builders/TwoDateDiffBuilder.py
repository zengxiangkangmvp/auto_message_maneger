import matplotlib.pyplot as plt
import datetime
import re
from .builder import pd, template, Builder, format_num, format_percent, Row, Ul, Img


class TwoDateDiffBuilder(Builder):
    """
    {
    "describe": "对比某一列在两日差距的报表",
    "info":
        [
            {"name":"subject", "type": "text", "label": "邮件主题", "des":"邮件在收件箱中显示的标题"},
            {"name":"mainCol", "type": "text", "label": "对比列", "des": "主要进行对比的列"},
            {"name":"detailCol", "type": "text", "label": "细节列", "des": "主要列下方的细节列, 展示头部数据."},
            {"name":"dateCol", "type": "text", "label": "日期列", "des": "使用哪个日期列查询"},
            {"name":"valCol", "type": "text", "label": "数值列", "des": "对哪个列进行计算对比"},
            {"name":"linkCol", "type": "text", "label": "链接列", "des": "使用哪个列作为链接参数"},
            {"name":"linkExpr", "type": "text", "label": "链接模板", "des": "python的可替换语句, 携带 %s 替换为完整语句 "},
            {"name":"showDetails", "type": "text", "label": "细节位数", "des": "排名靠前的多少位展示细节列?"},
            {"name":"detailLimit", "type": "number", "label": "细节数量", "des":"展示多少条细节?" },
            {"name":"threshold", "type": "number", "label": "阈值", "des": "判断是否是大幅上升下降的值, 5% 需要写为 0.05, 超过1 则作为数值判断"},
            {"name":"distinct", "type": "checkbox", "label": "去重", "des": "是否在聚合函数中使用 distinct 关键字, 主要搭配 count."},
            {"name":"where", "type": "text", "label": "条件", "des": "额外的 where 条件, 不需要加 where 关键字"},
            {"name":"aggr", "type": "text", "label": "聚合函数", "des": "SQL中对数值列的聚合方式,默认sum."},
            {"name":"interval", "type": "number", "label": "日期间隔", "des": "和结束日期间隔的天数"},
            {"name":"dates", "type": "text", "label":"日期", "des": "可以指定时间值(较晚日期在前,逗号分隔),不输入则默认根据最大日期值和日期间隔选择."},
            {"name":"numFormat", "type":"text", "label":"数值格式", "des": "数字显示的格式,例如 %d %.2f%% 等"},
            {"name":"comment", "type": "textarea", "label": "注释"}
        ]
    }
    """

    def parse_alias(self, k):
        col = self.info[k]
        i = col.upper().rfind(" AS ")
        alias = col if i == -1 else col[i + 4 :]
        if alias[0] == "`" and alias[-1] == "`":
            alias = alias[1:-1]
        return alias

    def parse_expr(self, k):
        col = self.info[k]
        i = col.upper().rfind(" AS ")
        expr = ("`%s`" % col) if i == -1 else col[:i]
        return expr

    @property
    def main_col_alias(self):
        """主要汇总列的名称"""
        return self.parse_alias("mainCol")

    @property
    def main_col_expr(self):
        """主要汇总列的表达式"""
        return self.parse_expr("mainCol")

    @property
    def detail_col_alias(self):
        """细节汇总列的名称"""
        return self.parse_alias("detailCol")

    @property
    def detail_col_expr(self):
        """细节汇总列的表达式"""
        return self.parse_expr("detailCol")

    @property
    def date_col_expr(self):
        """日期列的表达式"""
        return self.parse_expr("dateCol")

    @property
    def date_col_alias(self):
        """日期列名称"""
        return self.parse_alias("dateCol")

    @property
    def val_col_expr(self):
        """数值列表达式"""
        return self.parse_expr("valCol")

    @property
    def val_col_alias(self):
        """数值列名称"""
        return self.parse_alias("valCol")

    @property
    def show_details(self):
        if "detailCol" not in self.info:
            return 0
        if str.strip(self.info.get("detailCol", "")) == "":
            return 0
        return self.info.get("showDetails", 0)

    @property
    def detail_limit(self):
        return self.info.get("detailLimit", 0)

    @property
    def threshold(self):
        return self.info.get("threshold", 1)

    @property
    def distinct(self):
        result = self.info.get("distinct", False)
        result = "distinct " if result else ""
        return result

    @property
    def where(self):
        return self.info.get("where", "")

    @property
    def aggr(self):
        return self.info.get("attr", "sum")

    @property
    def interval(self):
        return self.info.get("interval", 0)

    @property
    def dates(self):
        """日期,第一个为最近的日期,第二个为较远的日期"""
        dates = self.info.get("dates", None)
        if dates is not None and "," in dates:
            dates = dates.split(",")
        return dates or self.get_dates()

    @property
    def table(self):
        return self.info["table"]

    @property
    def msg_title(self):
        return self.info.get("subject", "")

    def get_dates(self):
        """
        根据指定的间隔获取两个统计日期的文本
        如果未指定则获取最近的两个日期
        如果指定了间隔则获取 最近日期, 最近日期 - 间隔天数 后的最大日期
        """
        sql = self.make_date_sql()
        eng = self.db_engine
        now = eng.execute(sql).fetchall()[0][0]
        assert pd.notna(now), "未获取到有效日期值"

        if isinstance(now, int):
            lower = now - self.interval
        elif isinstance(now, (datetime.datetime, datetime.date)):
            lower = now - datetime.timedelta(days=self.interval)
        elif isinstance(now, str):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", now):
                now = datetime.date.fromisoformat(now)
                lower = now - datetime.timedelta(days=self.interval)
            else:
                raise ValueError("日期列字符串不是 yyyy-mm-dd 格式")
        else:
            raise TypeError("日期列是 int, date, datetime 以外的数据类型")
        sql = self.make_date_sql(lower)
        last = eng.execute(sql).fetchall()[0][0]
        eng.dispose()

        assert_info = "%s 前推%d日(%s)没有统计数据" % (str(now), self.interval, str(last),)
        assert pd.notna(last), assert_info

        self.info["dates"] = "%s,%s" % (str(now), str(last))
        return self.dates

    def make_date_sql(self, *args):
        """查询日期列表的sql"""
        if len(args) > 0:
            date = str(args[0])
        else:
            date = None

        date_col = self.date_col_expr
        table = self.info["table"]
        where = self.where
        compare = "<=" if date is None else "<"

        upper_tuple = (date_col, compare, date)
        upper = "" if date is None else " WHERE %s %s '%s' " % upper_tuple
        conj = "WHERE " if upper == "" else "AND "
        where = "" if where == "" else (" %s (%s) " % (conj, where))

        sql_tuple = (date_col, table, upper, where)
        sql = "select max(%s) as d from `%s` %s %s" % sql_tuple

        return sql

    @property
    def figures(self):
        """生成日期的横向条形图"""
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        self.df["increaseAbs"] = self.df["increase"].abs()
        d1 = self.df.sort_values("increaseAbs", ascending=False).iloc[0:10]
        d1 = d1[[self.main_col_alias, "now", "last"]]
        d1.index = d1[self.main_col_alias]
        del d1[self.main_col_alias]
        d1.columns = self.dates
        ax = d1.plot.barh()
        ax.grid()
        plt.tight_layout()
        return {"chart1": plt}

    def make_group_sql(self):
        """生成按第一级 group by 的 sql"""
        where = "" if self.where == "" else "AND (%s)" % self.where
        sql = """
            SELECT a.`{alias}` ,
                   coalesce(`last`,0) as `last`,
                   coalesce(`now`,0) as `now`,
                   coalesce(`now`,0) - coalesce(`last`,0) as `increase`,
                  (coalesce(`now`,0) - coalesce(`last`,0)) / coalesce(`last`,0) as `ratio`
            FROM (select {expr} as `{alias}`,
                         coalesce({aggr}({distinct}ifnull({val_col},0)),0) as `last`
                    from `{table}`
                   where {dt_col} = '{last}' {and_where}
                group by {expr}) as a
                INNER JOIN
                 (select {expr} as `{alias}`,
                         coalesce({aggr}({distinct}ifnull({val_col},0)),0) as `now`
                    from `{table}`
                   where {dt_col} = '{now}' {and_where}
                group by {expr}) as b on a.`{alias}` = b.`{alias}`
            """.format(
            last=self.dates[1],
            now=self.dates[0],
            expr=self.main_col_expr,
            alias=self.main_col_alias,
            val_col=self.val_col_expr,
            aggr=self.aggr,
            distinct=self.distinct,
            table=self.table,
            dt_col=self.date_col_expr,
            and_where=where,
        )
        return sql

    def make_all_diff_sql(self):
        """生成整体变化的sql"""
        where = self.info.get("where", "")
        where = "" if where == "" else " AND (%s)" % where
        sql = """
            select {dt_expr} as {dt_alias},
                   coalesce({aggr}({distinct}ifnull({val_col},0)),0) as `val`
            from `{table}`
            where {dt_expr} in ('{now}','{last}') {and_where}
            group by {dt_expr}
            order by {dt_alias} desc
            """.format(
            dt_expr=self.date_col_expr,
            dt_alias=self.date_col_alias,
            aggr=self.aggr,
            distinct=self.distinct,
            val_col=self.val_col_expr,
            table=self.table,
            now=self.dates[0],
            last=self.dates[1],
            and_where=where,
        )
        return sql

    def make_detail_sql(self, increase, parent):
        """单项细节的sql"""
        where = "" if self.where == "" else (" AND (%s) " % self.where)
        sub_table = "b" if increase else "a"
        _join = "right" if increase else "left"
        order = "desc" if increase else ""

        if self["linkCol"] is None:
            link_expr = "null"
        else:
            link_expr = "max(%s)" % self.parse_expr("linkCol")

        sql = """
            select `{sub_table}`.`{alias}`,
                   `{sub_table}`.`link`,
                   coalesce(`last`, 0) as `last`,
                   coalesce(`now`, 0) as `now`,
                   coalesce(`now`,0) - coalesce(`last`,0) as `increase`,
                  (coalesce(`now`,0) - coalesce(`last`,0)) / (coalesce(`last`, 0)) as `ratio`
            from (select {expr} as `{alias}`,
                         {aggr}({distinct}ifnull({val_col}, 0)) as `last`,
                         {link_expr} as `link`
                    from `{table}`
                   where {dt_col} = '{last}'
                     and {parent_col} = '{parent}' {and_where}
                group by {expr}) as a
                {left_or_right} join
                 (select {expr} as `{alias}`,
                         {aggr}({distinct}ifnull({val_col}, 0)) as `now`,
                         {link_expr} as `link`
                    from `{table}`
                   where {dt_col} = '{now}'
                     and {parent_col} = '{parent}' {and_where}
                group by {expr}) as b on a.`{alias}` = b.`{alias}`
            order by `increase` {order}
            limit {limit}
        """.format(
            sub_table=sub_table,
            expr=self.detail_col_expr,
            alias=self.detail_col_alias,
            aggr=self.aggr,
            val_col=self.val_col_expr,
            distinct=self.distinct,
            table=self.table,
            dt_col=self.date_col_expr,
            last=self.dates[1],
            now=self.dates[0],
            and_where=where,
            parent_col=self.main_col_expr,
            parent=parent,
            left_or_right=_join,
            order=order,
            limit=self.detail_limit,
            link_expr=link_expr,
        )
        return sql

    def add_describe(self, df, set_link=False):
        """为df添加一个说明列"""
        num_format = self["numFormat"]
        df["describe"] = (
            df[df.columns[0]]
            + ": "
            + df["last"].apply(lambda x: format_num(x, False, num_format))
            + " -> "
            + df["now"].apply(lambda x: format_num(x, False, num_format))
            + " ( "
            + df["increase"].apply(lambda x: format_num(x, True, num_format))
            + ", "
            + df["ratio"].apply(format_percent)
            + " )"
        )
        if set_link and self["linkCol"] is not None:
            link = self.info.get("linkExpr", "%s")

            def as_a(s):
                if pd.isna(s["link"]):
                    return s["describe"]
                else:
                    href = link % str(s["link"])
                    result = '<a href="%s">%s</a>'
                    return result % (href, s["describe"])

            df["describe"] = df.apply(as_a, axis=1)

    def read_data(self):
        """从数据库读取数据"""
        self.df = self.query(self.make_group_sql())
        self.df_total = self.query(self.make_all_diff_sql())
        self.add_describe(self.df)
        return self.df

    @property
    def total_row(self):
        """获取整体的变动情况"""
        df = self.df_total
        last = df["val"][1]
        now = df["val"][0]
        diff = now - last
        ratio = None if last == 0 else diff / last
        describe = [format_num(last, False, self["numFormat"])]
        describe.append(" -> ")
        describe.append(format_num(now, False, self["numFormat"]))
        describe.append(" ( ")
        describe.append(format_num(diff, nstr=self["numFormat"]))
        describe.append(", ")
        describe.append(format_percent(ratio))
        describe.append(" )")
        describe = "".join(describe)
        result = Row("%s 整体变动情况" % self.val_col_alias, "<li>%s</li>" % describe)
        return result

    @property
    def chart_row(self):
        """图片行"""
        img = Img("chart1", "%s对比图表" % self.main_col_alias)
        result = Row("", str(img))
        return result

    def detail(self, parent, increase):
        """生成一个子项的列表"""
        if self.show_details == 0:
            return ""
        increase = parent["increase"] >= 0 if increase == "auto" else increase
        name_col = self.main_col_alias
        sql = self.make_detail_sql(increase, parent[name_col])
        df = self.query(sql)
        self.add_describe(df, True)
        detail = Ul(df["describe"], fontSize=14)
        return "<li>%s%s</li>" % (parent["describe"], str(detail))

    def details(self, parents, increase):
        """生成 增长/减少/变化不大 三个大类目的 ul"""
        i = self.show_details
        with_details = parents.iloc[:i].to_dict(orient="record")
        with_details = map(lambda x: self.detail(x, increase), with_details)
        without_details = parents["describe"][i:].to_list()
        without_details = map(lambda x: "<li>%s</li>" % x, without_details)
        result = ["<ul>"]
        result.extend(list(with_details))
        result.extend(list(without_details))
        result.append("</ul>")
        return "".join(result)

    @property
    def df_increase(self):
        """增长大于等于阈值的条目:DataFrame"""
        col = "ratio" if self.threshold <= 1 else "increase"
        df = self.df[self.df[col] >= self.threshold]
        return df.sort_values("increase", ascending=False)

    @property
    def df_decrease(self):
        """减少大于等于阈值的条目:DataFrame"""
        col = "ratio" if self.threshold <= 1 else "increase"
        df = self.df[self.df[col] <= 0 - self.threshold]
        return df.sort_values("increase", ascending=True)

    @property
    def df_normal(self):
        """变化未超过阈值的条目:DataFrame"""
        col = "ratio" if self.threshold <= 1 else "increase"
        df = self.df[self.df[col].abs() < self.threshold]
        return df.sort_values("increase", ascending=False)

    def __make_title__(self, txt):
        """给每行创建一个标题"""
        if self.threshold > 1:
            t = format_num(self.threshold, False, self["numFormat"])
            return "%s %s %s:" % (self.val_col_alias, txt, t,)
        else:
            return "%s %s %.2f%%:" % (self.val_col_alias, txt, self.threshold * 100)

    @property
    def increase_row(self):
        """增长大于或者低于阈值的行:Row"""
        title = self.__make_title__("增加超")
        body = self.details(self.df_increase, True)
        row = Row(title, body)
        return row

    @property
    def decrease_row(self):
        """减少速率大于或者等于阈值的行:Row"""
        title = self.__make_title__("减少超")
        body = self.details(self.df_decrease, False)
        row = Row(title, body)
        return row

    @property
    def normal_row(self):
        """变化率的绝对值低于阈值的行:Row"""
        title = title = self.__make_title__("变动低于")
        body = self.details(self.df_normal, "auto")
        row = Row(title, body)
        return row

    def make_html(self):
        """
        生成报告的 html
        """
        title = "- %s ( %s 至 %s ) -" % (
            self.val_col_alias,
            self.dates[1],
            self.dates[0],
        )
        rows = [
            self.total_row,
            self.chart_row,
            self.increase_row,
            self.decrease_row,
            self.normal_row,
            self.comment_row,
        ]
        rows = map(lambda x: str(x), rows)
        rows = "\n".join(list(rows))
        result = template.format(title=title, rows=rows)
        return result
