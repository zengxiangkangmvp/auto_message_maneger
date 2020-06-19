import sqlalchemy
import pandas as pd
from . import mime
from .color import is_satisfy, parse_rules

template = """
    <table style="background-color:#FFFFFF;">
        <tr>
            <td>
                <h1 style="font-size: 20px;text-align:center;">{title}</h1>
                <hr />
            </td>
        </tr>
        {rows}
        <tr>
            <td>
                <hr style="margin-top: 20px;" />
                <p style="text-align: center;">- 本邮件由系统自动发送,请勿回复. -</p>
            </td>
        </tr>
    </table>
"""


def html(x):
    """
    将某个数值转换为 html 字符
    """
    if pd.isna(x):
        return ""
    if not isinstance(x, str):
        x = str(x)
    if "&" in x:
        x = x.replace("&", "&amp;")
    if "<" in x:
        x = x.replace("<", "&lt;")
    if ">" in x:
        x = x.replace(">", "&gt;")
    if '"' in x:
        x = x.replace('"', "&quot;")
    if "'" in x:
        x = x.replace("'", "&apos;")
    return x


def make_td(x, rules=[]):
    t = html(x)
    for symbol, val, color in rules:
        if is_satisfy(x, symbol, val):
            return f'<td style="background-color:{color}">{t}</td>'
    return f"<td>{t}</td>"


def make_html(data, rules={}):
    """
    将 pd.DataFrame 转换为 html 表格
    根据 rules 会设置不同的单元格颜色
    """
    df = data.copy()
    for col in df.columns:
        df[col] = df[col].apply(lambda x: make_td(x, rules.get(col, [])))
    html = df.apply(lambda x: f"<tr>{''.join(x)}</tr>", axis=1)
    ths = "".join(df.columns.to_series().apply(lambda x: f"<th>{x}</th>"))
    html = "\n".join(html)
    result = (
        f'<table border="1" style="border-collapse:collapse">\n'
        f"<thead><tr>{ths}</tr></thead>\n"
        f"<tbody>\n{html}\n</tbody></table>"
    )
    return result


def format_num(num, with_pre=True, nstr=None):
    """
    将数字格式化为文本

    Args:
        with_pre: 是否带前置 '+' 符号
        nstr: 可替换的格式化字符串比如 .2f%% 一类
    """
    if pd.isna(num):
        return ""

    num = float(num)
    if abs(num - int(num)) < 0.01:
        num = int(num)
    else:
        num = round(num, 2)

    pre = "+" if (num > 0 and with_pre) else ""

    if nstr is not None:
        return pre + (nstr % num)

    if abs(num) > 9999:
        return "%s%.2f万" % (pre, num / 10000)
    else:
        return f"{pre}{num}"


def format_percent(num):
    if pd.isna(num):
        return ""
    return ("+" if num > 0 else "") + "%.2f%%" % (num * 100)


def format_file_name(f_name):
    dt = pd.Timestamp.today()
    yyyy = str(dt.year)
    mm = str(dt.month) if dt.month > 9 else f"0{dt.month}"
    dd = str(dt.day) if dt.day > 9 else f"0{dt.day}"
    ww = str(dt.weekofyear)
    f_name = (
        f_name.replace("YYYY", yyyy)
        .replace("MM", mm)
        .replace("DD", dd)
        .replace("WW", ww)
    )
    return f_name


class Img(object):
    """代表图片标签的类"""

    def __init__(self, cid, alt):
        self.cid = cid
        self.alt = alt

    def __str__(self):
        t = '<img src="cid:%s" alt="%s" />'
        t = t % (self.cid, self.alt)
        return t


class Row(object):
    """代表一行的类"""

    def __init__(self, title, main):
        self.title = title
        self.main = main

    def __str__(self):
        t = '<tr><td><h2 style="font-size: 17px;margin-bottom: 1px;">%s</h2>%s</td></tr>'
        result = t % (self.title, self.main)
        return result

    def __repr__(self):
        result = "%s:\n%s" % (self.title, self.main)
        return result


class Ul(object):
    """<ul>元素的类"""

    def __init__(self, data, fontSize=16):
        self.data = list(data)
        self.fontSize = fontSize

    def __str__(self):
        li = "\n".join(list(map(lambda x: "<li>" + x + "</li>", self.data)))
        t = '<ul style="margin-top: 1px;font-size:%dpx">\n%s\n</ul>'
        return t % (self.fontSize, li)

    def __repr__(self):
        return "\n".join(self.data)


class Builder(object):
    """报告生成器的基类 提供基础的报表构建方法"""

    def __init__(self, info, connstr=""):
        self.connstr = connstr
        self.info = info
        self.df = pd.DataFrame()

    def __getitem__(self, k):
        return self.info.get(k, None)

    @property
    def db_engine(self):
        conn_str = self.connstr % self.info["database"]
        return sqlalchemy.create_engine(conn_str)

    @property
    def figures(self):
        """
        返回图片的字典, key 为 html 中的 cid, value 提供 savefig 方法的对象, 比如 plt 或者 figure
        """
        return {}

    @property
    def df_attachments(self):
        """
        返回附件的字典, key 为文件名, value n行2列的列表, 列1为 工作表名, 列2 为 DataFrame
        例: {"xxx明细": [["明细", df1], ["说明", df2]]}
        """
        return {}

    @property
    def file_attachments(self):
        """
        其余文件类型附件, key 为附件名, value 为附件地址
        """
        files = self["local_attach"]
        if files is None:
            return {}
        files = [f.strip() for f in files.strip().split("\n")]
        result = {}
        for f in files:
            if f == "":
                continue
            slash = f.rfind("\\")
            dot = f.rfind(".")
            assert slash > -1 and dot > slash, "文件路径异常"
            f_name = f[slash + 1 :]
            f_name = format_file_name(f_name)
            f = f[: slash + 1] + f_name
            result[f_name] = f
        return result

    @property
    def need_post(self):
        """
        报告是否需要发送的实现,默认True
        """
        return True

    @property
    def msg_title(self):
        """
        报表的邮件标题
        """
        return ""

    @property
    def comment_row(self):
        """邮件最末的注释行"""
        if self["comment"] is None:
            return ""
        else:
            content = self["comment"].replace(" ", "&nbsp;")
            content = content.replace("\n", "<br />")
            return "<tr><td>%s</td></tr>" % content

    def query(self, sql, index=None):
        """
        执行一个查询
        """
        eng = self.db_engine
        sql = sql.replace(r"%", r"%%")
        result = pd.read_sql(sql, self.db_engine, index_col=index)
        eng.dispose()
        return result

    def test_before_read(self):
        """
        在发送前执行一次 SQL 测试, 只有查询到数据并且数据全部为 True 才可通过
        """
        try:
            if self["testSql"] is None:
                return None
            else:
                df = self.query(self["testSql"])
                assert df.shape[0] > 0, "SQL检查未查询到数据,邮件未发送."
                assert df.all().all(), "SQL检查有 False 值,邮件未发送."
                return None
        except Exception as e:
            raise Exception("发送前的SQL检验未通过:\n%s" % repr(e))

    def read_data(self):
        """
        获取数据动作
        """
        pass

    def make_html(self):
        """
        生成报表的html部分
        """
        return self.df.to_html()

    def make_report(self):
        """
        生成邮件的消息主体
        首先生成主体内容
        然后添加 图片, DataFrame, 文件附件
        接着返回 From 为空的 MIMEMultipart
        """
        title = self.msg_title
        content = self.make_html()
        msg = mime.make_msg(title, content)

        figures = self.figures
        for i in figures:
            msg = mime.attach_figure(msg, i, figures[i])

        file_attachments = self.file_attachments
        if len(file_attachments) > 0:
            for i in file_attachments:
                msg = mime.attach_file(msg, i, file_attachments[i])
        else:
            dfs = self.df_attachments
            for i in dfs:
                msg = mime.attach_df(msg, i, dfs[i])

        return msg
