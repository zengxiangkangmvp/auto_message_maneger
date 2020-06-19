# -*- coding: utf-8 -*-
import json
import sqlalchemy
import datetime
import traceback
import re
from os import environ
from smtplib import SMTP_SSL
from email.utils import COMMASPACE
from traceback import format_exc
from email.mime.text import MIMEText

from builders import builder_dict

MAIL_ACCOUNTS = r"\Documents\auto_message_maneger\mails.json"
MAIL_ERR_LOG = r"\Documents\auto_message_maneger\mails_err.json"
DB_ACCOUNTS = r"\documents\auto_message_maneger\dbs.json"
ERROR_RECEIVER = "1510646063@qq.com"


def read_json(path):
    fp = open(path, encoding="utf-8")
    result = json.load(fp)
    fp.close()
    return result


def get_connstr(account="mysql"):
    path = environ["USERPROFILE"] + DB_ACCOUNTS
    db = read_json(path)[account]
    t = (db["user"], db["pwd"], db["server"])
    conn_str = "mysql+pymysql://%s:%s@%s/%%s" % t
    return conn_str


def get_engine(schema="auto_message_maneger"):
    """获取数据库的信息"""
    connstr = get_connstr()
    connstr = connstr % schema
    eng = sqlalchemy.create_engine(connstr)
    return eng


def in_day_range(days, weekdays):
    """
    根据 day 与 weekday 判断当前是否是符合 day 与 weekday 的日期

    Args:
        day: 每月的第几天
        weekday: 每周第几天, 起始为周一, 用 1,2,3,4,5,6,7 表示
    """
    if days == "" and weekdays == "":
        return True

    t = datetime.date.today()
    weekday = str(t.weekday() + 1)
    day = str(t.day)

    if weekday in weekdays.split(","):
        return True

    if day in days.split(","):
        return True

    return False


def get_reports(time):
    """
    Args:
        time: 当前时间离开今日 00:00 的秒数
    """
    try:
        sql = """SELECT id,name,receiver,builder_name,info,post_day,post_weekday,creator
                   FROM auto_message_maneger.reports
                  WHERE post_time < %s
                    AND complete_time is null
                    AND delete_time is null"""
        eng = get_engine()
        rpts = eng.execute(sql, (time)).fetchall()
        result = []
        for Id, name, receiver, builder, info, days, weekdays, creator in rpts:
            if in_day_range(days, weekdays):
                info = json.loads(info)
                x = {
                    "name": name,
                    "builder_name": builder,
                    "info": info,
                    "id": Id,
                    "receiver": receiver,
                    "creator": creator,
                }
                result.append(x)
        eng.dispose()
        return result
    except Exception as e:
        add_db_errlog("无法获取报表信息.(%s)" % repr(e))
        add_local_errlog("无法获取报表信息.(%s)" % repr(e), ERROR_RECEIVER)
        return []


def get_login_info():
    path = environ["USERPROFILE"] + MAIL_ACCOUNTS
    info = read_json(path)["remindservices"]
    host_server = info["host_server"]
    sender = info["mail"]
    pwd = info["pwd"]
    return host_server, sender, pwd


def get_smtp(server: str, uid: str, pwd: str):
    """
    获取已经登入的 smtp 对象

    Returns:
        SMTP_SSL服务器对象
    """
    smtp = SMTP_SSL(server)
    smtp.set_debuglevel(0)
    smtp.ehlo(server)
    smtp.login(uid, pwd)
    return smtp


def send_mail(smtp: SMTP_SSL, msg, sender, receiver: (str, list, tuple)):
    """
    发送邮件, 该模块中所有的邮件发送都是调用此方法进行发送

    Args:
        smtp: 已经登入的smtp服务器
        msg : 邮件消息主体 MIMEMultipart
        receiver : 接收人 可以是 文本 或者 列表
    """
    assert isinstance(receiver, (str, list, tuple)), "接收人信息并非文本或列表"

    if isinstance(receiver, str):
        receiver = receiver.split(",")

    if isinstance(receiver, (list, tuple)):
        msg["To"] = COMMASPACE.join(receiver)
        smtp.sendmail(sender, receiver, msg.as_string())
        return COMMASPACE.join(receiver) + " post success."


def parse_receiver(txt):
    """
    解析字符串为接收邮箱列表
    源字符串格式应为:  人名1:邮箱1,人名2:邮箱2
    """
    pattern = r"[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+\.\w+"
    result = re.findall(pattern, txt)
    assert len(result) > 0, "邮件接收人为空"
    return result


def read_local_errlog(path=MAIL_ERR_LOG):
    """
    读取本地的错误记录
    """
    path = environ["USERPROFILE"] + path
    logs = []
    try:
        logs = read_json(path)
    except FileNotFoundError:
        fp = open(path, "w", encoding="utf-8")
        json.dump([], fp, ensure_ascii=False)
        fp.close()
    return logs


def add_local_errlog(err, creator=None, path=MAIL_ERR_LOG):
    """
    在本地添加一条错误记录

    Args:
        err: str 错误的描述
        path: 错误日志的路径
    """
    try:
        creator = str(creator)
        path = environ["USERPROFILE"] + path
        logs = read_local_errlog()
        time = str(datetime.datetime.now())[:-7]
        logs.append({"time": time, "creator": creator, "error": err})
        fp = open(path, "w", encoding="utf-8")
        json.dump(logs, fp, ensure_ascii=False)
        fp.close()
        return "Added."
    except Exception:
        return "add local error log failed. (%s)" % format_exc()


def try_post(receiver, builder, info):
    """
    发送一条测试邮件, 并返回发送成功或者错误的信息
    """
    try:
        server, sender, pwd = get_login_info()
        connstr = get_connstr()
        builder = builder_dict[builder](info, connstr)
        builder.test_before_read()
        builder.read_data()
        msg = builder.make_report()
        msg["From"] = sender
        smtp = get_smtp(server, sender, pwd)
        return send_mail(smtp, msg, sender, receiver)
    except Exception:
        return traceback.format_exc()


def add_db_errlog(err, table="err_logs"):
    try:
        sql = f"INSERT INTO `{table}`(repr) VALUES(%s)"
        eng = get_engine()
        eng.execute(sql, (err))
        eng.dispose()
        return "Added."
    except Exception:
        return "Add log to db failed. (%s)" % format_exc()


def add_db_complete(Id, posted=True):
    time = get_now_seconds() if posted else 99999
    sql = "UPDATE reports SET complete_time = %s where id = %s"
    eng = get_engine()
    eng.execute(sql, (time, Id))
    eng.dispose()
    return "Added."


def add_db_postlog(Id, trigger):
    sql = "INSERT INTO post_logs(`report_id`, `trigger`) VALUES(%s,%s)"
    eng = get_engine()
    eng.execute(sql, (Id, trigger))
    eng.dispose()
    return "Added."


def get_now_seconds():
    now = datetime.datetime.now()
    time = now.hour * 3600 + now.minute * 60 + now.second
    return time


def scan_err(path=MAIL_ERR_LOG):
    """查询本地的错误记录, 如果有则把错误记录发送给模块开头定义的错误处理者"""
    logs = read_local_errlog(path)
    new_errs = [x for x in logs if x.get("reported", False) is False]
    for err in new_errs:
        txt = str(err)
        txt = path + "\n\n" + txt
        msg = MIMEText(txt, "plain", "utf-8")
        server, sender, pwd = get_login_info()
        smtp = get_smtp(server, sender, pwd)

        try:
            receiver = parse_receiver(err.get("creator", ""))
        except Exception:
            receiver = ERROR_RECEIVER

        send_mail(smtp, msg, sender, receiver)

    for l in logs:
        l["reported"] = True

    fp = open(environ["USERPROFILE"] + path, "w", encoding="utf-8")
    json.dump(logs, fp, ensure_ascii=False)
    fp.close()


def post_one(report, trigger=environ["COMPUTERNAME"]):
    server, sender, pwd = get_login_info()
    connstr = get_connstr()

    try:
        assert "id" in report, "无 id 的报表无法进行投递."
        builder = report["builder_name"]
        info = report["info"]
        info["attach_name"] = report["name"]  # 领导的要求, 去TM的附件必须要用报表名
        receiver = parse_receiver(report["receiver"])
        builder = builder_dict[builder](info, connstr)
        builder.test_before_read()  # 查询前的数据检验
        builder.read_data()  # 读取数据
        if builder.need_post:
            msg = builder.make_report()
            msg["From"] = sender
            smtp = get_smtp(server, sender, pwd)
            result = send_mail(smtp, msg, sender, receiver)
            add_db_complete(report["id"], True)
            add_db_postlog(report["id"], trigger)
            return result
        else:
            add_db_complete(report["id"], False)
            return "根据内容判断该邮件无需投递."
    except Exception:
        Id = report.get("id", "")
        name = report.get("name", "")
        creator = report.get("creator", ERROR_RECEIVER)
        err = json.dumps(
            {"id": Id, "name": name, "tb": format_exc()}, ensure_ascii=False
        )
        add_db_errlog(err)
        add_local_errlog(err, creator)
        return "生成过程出现错误, 已记录到日志."


if __name__ == "__main__":
    time = get_now_seconds()
    if time > 21600:
        reports = get_reports(time)

        for report in reports:
            post_one(report)
        scan_err()
