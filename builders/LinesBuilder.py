from .builder import pd, Builder, template
import json
import matplotlib.pyplot as plt
import datetime
from matplotlib.ticker import FuncFormatter


def x_val_formatter(x):
    if isinstance(x, str):
        return x
    if x.hour == 0 and x.minute == 0:
        return str(x)[:10]
    return str(x)[:16]


def num_formatter(x, keep2=True):
    if pd.isna(x):
        return "<NA>"
    if abs(x) > 9999:
        if keep2:
            return "%.2f万" % (x / 10000)
        else:
            return "%d万" % (x / 10000)
    return str(round(x, 2))


@FuncFormatter
def axis_formatter(x, pos):
    return num_formatter(x, False)


class LinesBuilder(Builder):
    """
    {
        "describe": "趋势线报表, 绘制数据线, 可添加要达到的目标点.",
        "info": [{"name":"title", "type": "text", "label": "标题", "des": "报表的标题"},
                 {"name":"name1", "type": "text", "label": "指标1", "des": "指标1的名称"},
                 {"name":"SQL1", "type": "text", "label": "SQL1", "des": "获取指标1数据的 GROUP BY 语句, 列1是时间或者数值, 列2是指标的值"},
                 {"name":"targets1", "type": "text", "label": "目标1", "des": "指标1的目标, 可以使用单个数值绘制横线,\\n或者使用嵌套列表例如 [[\\"2020-03-09\\", 1243]] 绘制折线\\n日期必须使用双引号"},
                 {"name":"cum1", "type": "checkbox", "label": "是否累加1", "des": "指标1是否使用累加方式计算\\n常见于将多个日期的数值累积计算最终的目标值"},
                 {"name":"name2", "type": "text", "label": "指标2", "des": "指标2的名称"},
                 {"name":"SQL2", "type": "text", "label": "SQL2", "des": "获取指标2数据的 GROUP BY 语句, 列1是时间或者数值, 列2是指标的值"},
                 {"name":"targets2", "type": "text", "label": "目标2", "des": "指标2的目标, 可以使用单个数值绘制横线,\\n或者使用嵌套列表例如 [[\\"2020-03-09\\", 1243]] 绘制折线\\n日期必须使用双引号"},
                 {"name":"cum2", "type": "checkbox", "label": "是否累加2", "des": "指标2是否使用累加方式计算"},
                 {"name":"name3", "type": "text", "label": "指标3", "des": "指标3的名称"},
                 {"name":"SQL3", "type": "text", "label": "SQL3", "des": "获取指标3数据的 GROUP BY 语句, 列1是时间或者数值, 列2是指标的值"},
                 {"name":"targets3", "type": "text", "label": "目标3", "des": "指标3的目标, 可以使用单个数值绘制横线, 或者使用嵌套列表例如 [[\\"2020-03-09\\", 1243]] 绘制折线\\n日期必须使用双引号"},
                 {"name":"cum3", "type": "checkbox", "label": "是否累加3", "des": "指标3是否使用累加方式计算"},
                 {"name":"comment", "type": "textarea", "label": "注释"}]
    }
    """

    def set_df_dtype(self, df):
        """
        返回 df 第一列的第一个值, 以及重设 df 第一列的 dtype,
        只允许 int 和 datetime64 两种类型
        """
        col = df.columns[0]
        x = df[col][0]
        if "int" in str(type(x)):
            df[col] = df[col].astype(str)
        else:
            df[col] = df[col].astype("datetime64")
        first = df.iloc[0][0:2]
        last = df.iloc[-1][0:2]
        return df, first, last

    def read_data(self):
        """对于提供了 SQL 的信息读取数据, 添加到 dataset 列表中"""
        self.dataset = []
        for i in range(1, 4):
            name = "name%d" % i
            SQL = "SQL%d" % i
            targets = "targets%d" % i
            cum = "cum%d" % i
            if SQL in self.info:
                df = self.query(self.info[SQL]).dropna()
                if df.shape[0] == 0:
                    continue
                df = df.sort_values(by=df.columns[0])
                df, first, last = self.set_df_dtype(df)

                cum = self.info.get(cum, False)
                if cum:
                    df[df.columns[1]] = df[df.columns[1]].cumsum()

                self.dataset.append(
                    {
                        "name": self.info.get(name, "指标"),
                        "df": df,
                        "targets": self.read_targets(targets, first, last),
                    }
                )
            else:
                continue

    def read_targets(self, k, first, last):
        """
        根据 k 读取对应的 targets 信息并根据 first 的值设置 targets 序列

        Returns:
            {
                "method": 绘制目标时候调用的方法
                "data": 目标信息的数据, [[x轴的数据列表],[y轴的数据列表]]
            }
        """
        t = self.info.get(k, "null")
        if t == "null":
            return {}
        if isinstance(t, (int, float)):
            return {"method": "plot", "data": [[first[0], last[0]], [t, t]]}
        t = json.loads(t)
        x = [first[0]]
        y = [first[1]]
        for target in t:
            time = target[0]
            value = target[1]
            if isinstance(x[0], str):
                x.append(str(time))
            else:
                x.append(datetime.datetime.fromisoformat(str(time)))
            y.append(value)
        return {"method": "scatter", "data": [x, y]}

    def plotTargets(self, t):
        """
        绘制目标线或者目标点
        如果目标是单个数值则 绘制一条水平线并在末端加上注释
        如果目标是一组数值则 绘制一组 x 形散点, 并在散点上加上注释
        """
        if "data" not in t:
            return

        data = t["data"]
        method = t["method"]
        xs = data[0]
        ys = data[1]

        xyt = (-5, 5)  # 文本 offset 值
        txtc = "offset pixels"  # 文本 offset 方式
        c = "black"  # annotate 颜色

        if method == "plot":
            plt.plot(xs, ys, c="red", label="目标")
            txt = num_formatter(ys[1])
            xy = (xs[1], ys[1])
            plt.annotate(txt, xy, xytext=xyt, textcoords=txtc, c=c)

        if method == "scatter":
            plt.scatter(xs, ys, marker="x", c="red", label="目标")
            plt.plot(xs, ys, c="red")
            for x, y in zip(xs[1:], ys[1:]):
                txt = num_formatter(y)
                xyt = (-5, 5)
                plt.annotate(txt, (x, y), xyt, textcoords=txtc, c=c)

    def plotsub(self, i):
        """绘制一个子图"""
        sub = len(self.dataset) * 100 + 10 + i + 1
        plt.subplot(sub)
        data = self.dataset[i]
        df = data["df"]
        plt.plot(df[df.columns[0]], df[df.columns[1]], label=data["name"])
        self.add_title(data["name"], df, data["targets"])
        self.plotTargets(data["targets"])
        ax = plt.gca()
        ax.yaxis.set_major_formatter(axis_formatter)
        # plt.xticks(rotation=45)
        plt.grid()
        plt.legend()

    def add_title(self, name, df, targets):
        """给子图添加一个标题"""
        start_y = df.iloc[0][1]
        x, y = df.iloc[-1][:2]
        text = "%s: %s %s" % (name, x_val_formatter(x), num_formatter(y))
        percent = ""

        if targets.get("method") == "plot":
            target = targets["data"][1][-1]
            percent = " 完成比: %.2f%%" % ((y / target) * 100)

        if targets.get("method") == "scatter":
            increase = start_y < targets["data"][1][-1]
            target = self.find_recent_t(x, targets["data"])
            if increase and target is not None:
                percent = " 最近目标完成比: %.2f%%" % ((y / target) * 100)
            elif target is not None:
                complete = start_y - y
                total = start_y - target
                percent = " 最近目标完成比: %.2f%%" % ((complete / total) * 100)

        plt.title(text + percent, loc="left")

    def find_recent_t(self, x, targets):
        """搜索最近一个目标的数值"""
        ds = targets[0]
        vs = targets[1]
        for d, v in zip(ds, vs):
            if isinstance(x, str):
                if int(x) <= int(d):
                    return v
            if x <= d:
                return v
        return None

    @property
    def title(self):
        return self.info.get("title", "未命名报表")

    @property
    def msg_title(self):
        return self.title

    @property
    def figures(self):
        plt.clf()
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False
        dataCount = len(self.dataset)
        if dataCount == 0:
            return {}
        plt.figure(figsize=(7.2, dataCount * 3))
        for i in range(dataCount):
            self.plotsub(i)
        plt.subplots_adjust(hspace=0.57)
        plt.tight_layout()
        return {"chart1": plt}

    @property
    def df_attachments(self):
        k = self.info.get("attach_name", None) or self.title
        dfs = []
        for item in self.dataset:
            dfs.append([item["name"], item["df"]])
        return {k: dfs}

    def make_html(self):
        body = '<tr><td><img src="cid:chart1" alt="各指标折线图" /></td></tr>'
        body += self.comment_row
        html = template.format(title=self.title, rows=body)
        return html
