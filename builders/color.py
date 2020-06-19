import pandas as pd
import numpy as np


def parse_symbol(txt):
    """
    解析运算符以及数值
    解析颜色规则中去掉了颜色的部分, 例如 >12 ='12'
    规则说明:
        =null =>  '=', None
        >12  =>  '>',12
        >'12' =>  '>','12'
        >12% => '>',0.12
        >12Q => '>',0.12
    """
    txt = txt.replace(" ", "")
    i = 2 if txt[1] in ["=", ">"] else 1
    symbol = txt[:i]
    val = txt[i:]
    if (val[0] == val[-1] == "'") or (val[0] == val[-1] == '"'):
        val = str(val[1:-1])
    elif val in ["null", "NULL", "Null"]:
        val = None
    else:
        try:
            if "%" in val or "Q" in val:
                val = float(val[:-1]) / 100
                assert 1 >= val >= 0, "百分比或百分位指定必须小于等于100或大于等于0"
            else:
                val = float(val)
        except ValueError:
            raise ValueError(f"颜色规则中的值`{val}`无法被转换为数值")
    if not isinstance(val, float):
        assert symbol in ["=", "<>"], "非数值类颜色规则只能使用'=','<>'"
    assert symbol in [">", ">=", "=", "<>", "<", "<="], f"不支持的比较符号`{symbol}`"
    return symbol, val


def convert_num(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    assert isinstance(x, str), "非字符串无法进行列转换"
    if x == "":
        return np.nan
    if not str.isdigit(x[-1]):
        x = x[:-1]
    try:
        return float(x)
    except ValueError:
        return np.nan


def parse_rule(txts, s):
    """
    Args:
        txt: 文本, 支持格式 '>数值#AABBCC', '>百分比#AABBCC', '>百分位#AABBCC'
        s: pd.Series, 用于计算百分比或者百分位
    """
    txts = txts.replace(" ", "")
    rules = []
    for txt in txts.split(","):
        i = txt.find("#")
        assert i > -1, f"`{txt}`中未指定颜色值"
        color = txt[i:]
        txt = txt[:i]
        symbol, val = parse_symbol(txt)
        if isinstance(val, (int, float)) and s.dtype.name == "object":
            s = s.copy()
            s = s.apply(lambda x: convert_num(x)).astype(float)
        if "%" in txt:
            rng = abs(s.max() - s.min())
            val = rng * val
        if "Q" in txt:
            val = s.quantile(val)
        rules.append((symbol, val, color))
    return rules


def parse_rules(txt, df):
    """
    根据输入的规则文本生成规则
    输入类似于:
        列1:>12#AABBCC,<10#BBAACC
        列2:>90%#AABBCC

    这里每行使用一个列名, 每列使用逗号分隔多个规则, 每个规则由 比较符号,数值,颜色值组成
        比较符号: =, <>, <, <= , >, >=
        数值: 被比较的值, 可以是 数值, null, 文本, 百分比数值, 百分位数值
        颜色: #AABBCC 的十六进制颜色

    颜色可在网上搜索 '十六进制颜色' 得到对应的颜色代码

    例:
    >100#AABBCC  该列数值大于100的被设置为颜色 #AABBCC
    >50%#AABBCC  该列数值大于 最小值 + (最大值-最小值) * 0.5 的被设置为 #AABBCC
    >50Q#AABBCC  该列数值大于该列百分位数0.5 的被设置为 #AABBCC, 百分位数计算参考 pd 的 quantile()
    =null#AABBCC  pd.isna 为 True 的颜色被设置为 #AABBCC
    <>null#AABBCC  pd.notna 为 True 的颜色被设置为 #AABBCC
    ='严重'#AABBCC  文本值为 严重 的被设置为 #AABBCC

    这个是获取规则的函数链的起点.
    规则的限制如下:
        如果被比较的值为文本或者null, 则只能使用 =, <> 两种对比符号
        如果被比较的列为文本但是是 '12%' 这种类型, 会被去掉最后一个字符转换为数值进行计算比较
        如果被比较的列是数值, 则可以使用全部规则
    """
    if txt is None:
        return {}
    rules = {}
    rows = [t.strip() for t in txt.split("\n")]
    for row in rows:
        if row == "":
            continue
        i = row.find(":")
        assert i > -1, "颜色规则无冒号(必须是半角符号)"
        key = row[:i].strip()
        assert key in df.columns, f"对应数据表无`{key}`列"
        rules[key] = parse_rule(row[i + 1 :], df[key])
    return rules


def is_satisfy(x, symbol, val):
    """
    判断某数值与单条规则是否相等
    Args:
        x: 需要被判断的值
        symbol: 运算符号
        val: 规则中被比较的值
    """
    if val is None:
        if isinstance(x, str) and x == "":
            x = None
        if symbol == "=":
            return pd.isna(x)
        else:
            return pd.notna(x)

    if isinstance(val, str):
        if symbol == "=":
            return x == val
        else:
            return x != val

    if isinstance(val, (int, float)):
        if pd.isna(x):
            return False
        x = convert_num(x)
        if symbol == ">":
            return x > val
        if symbol == ">=":
            return x >= val
        if symbol == "=":
            return x == val
        if symbol == "<":
            return x < val
        if symbol == "<=":
            return x <= val

    return False
