from datetime import datetime
from post import read_json, get_login_info, get_engine, get_connstr
from post import builder_dict, get_smtp, parse_receiver, send_mail
from post import format_exc, environ, json, in_day_range, get_now_seconds

LOCAL_MAILS = environ["USERPROFILE"] + r"\Documents\auto_message_maneger\local_mails.json"


def check_mail(mail):
    """检查邮件是否符合数据类型规范"""
    check = {
        "id": int,
        "name": str,
        "post_time": int,
        "post_weekday": str,
        "post_day": str,
        "receiver": str,
        "remarks": str,
        "builder_name": str,
        "info": dict,
        "creator": str,
    }
    assert "complete_time" in mail, "邮件没有 complete_time 信息"
    for c in check:
        assert c in mail, f"邮件没有 {c} 信息"

    for c in mail:
        if c == "complete_time":
            if mail[c] is not None and not isinstance(mail[c], str):
                raise TypeError(f"邮件的`complete_time`不是`str`类型")
            continue

        if c in check:
            if not isinstance(mail[c], check[c]):
                raise TypeError(f"邮件的`{c}`不是`{check[c]}`类型.")
        else:
            del mail[c]
    return mail


def get_mails(comp="int"):
    """
    从文件中读取所有邮件

    Args:
        comp: complete_time 返回值的类型
              int: 页面渲染时候
              str: CRUD 的时候
              datetime: 发送邮件时候
    """
    try:
        assert comp in ["int", "str", "datetime"], "错误的compete_time数据类型"
        mails = read_json(LOCAL_MAILS)
        for m in mails:
            if m["complete_time"] is not None:
                t = datetime.fromisoformat(m["complete_time"])
                if comp == "int":
                    if t.date() == datetime.now().date():
                        m["complete_time"] = t.hour * 3600 + t.minute * 60
                    else:
                        m["complete_time"] = None
                if comp == "datetime":
                    m["complete_time"] = t
        return mails
    except FileNotFoundError:
        return []


def get_index(mails, id_):
    """ 根据 Id 定位某个邮件的索引, Id 和邮件所在位置没有直接关系 """
    for i in range(len(mails)):
        if mails[i].get("id") == id_:
            return i
    raise IndexError(f"未查找到id为{id_}的报表.")


def make_id(mails):
    """产生一个邮件的 id """
    id_array = [m.get("id", 0) for m in mails]
    try:
        return max(id_array) + 1
    except ValueError:
        return 1


def save(mails):
    """ 保存邮件的 json 列表 """
    fp = open(LOCAL_MAILS, "w", encoding="utf-8")
    json.dump(mails, fp, ensure_ascii=False)
    fp.close()
    return "save mail success."


def update(mail, keep_comp=True):
    mails = get_mails("str")
    i = get_index(mails, mail["id"])
    if keep_comp:
        old_time = mails[i]["complete_time"]
        mail["complete_time"] = old_time
    mail = check_mail(mail)
    mails[i] = mail
    save(mails)


def create(mail):
    """ 创建一个邮件 """
    mails = get_mails("str")
    id_ = make_id(mails)
    mail["id"] = id_
    mail["complete_time"] = None
    mail = check_mail(mail)
    mails.append(mail)
    save(mails)
    return id_


def delete(id_):
    mails = get_mails("str")
    try:
        i = get_index(mails, id_)
        mails.pop(i)
        save(mails)
        return 1
    except IndexError:
        return 0


def add_post_log(computer, id_, name, is_empty):
    try:
        sql = (
            "insert into local_post_logs(computer, report_id, report_name, is_empty)"
            " values(%s,%s,%s,%s)"
        )
        eng = get_engine()
        eng.execute(sql, (computer, id_, name, is_empty))
        eng.dispose()
    except Exception:
        pass


def set_complete(mail):
    mail["complete_time"] = str(datetime.now())[:-7]
    update(mail, False)


def post_all():
    """发送本地所有邮件"""
    mails = get_mails("datetime")
    for m in mails:
        if not in_day_range(m["post_day"], m["post_weekday"]):
            print(m["name"], "不在指定的每月几号或者星期几,不发送.")
            continue
        if m["post_time"] > get_now_seconds():
            print(m["name"], "指定的发送时间小于当前时间,不发送.")
            continue
        if (
            m["complete_time"] is None
            or m["complete_time"].date() < datetime.now().date()
        ):
            print(m["name"], "开始处理")
            post_one(m)
        else:
            print(m["name"], "今日已经发送过,不再次发送.")


def post_one(report, trigger=environ["COMPUTERNAME"]):
    server, sender, pwd = get_login_info()
    connstr = get_connstr()

    try:
        assert "id" in report, "无 id 的报表无法进行投递."
        builder = report["builder_name"]
        info = report["info"]
        info["attach_name"] = report["name"]
        receiver = parse_receiver(report["receiver"])
        builder = builder_dict[builder](info, connstr)
        builder.test_before_read()  # 查询前的数据检验
        builder.read_data()  # 读取数据
        if builder.need_post:
            msg = builder.make_report()
            msg["From"] = sender
            smtp = get_smtp(server, sender, pwd)
            result = send_mail(smtp, msg, sender, receiver)
            set_complete(report)
            add_post_log(
                trigger,
                report["id"],
                report.get("name", "") + " - " + builder.msg_title,
                False,
            )
            print(f"`{report['name']}` 已经发送.")
            return result
        else:
            add_post_log(
                trigger,
                report["id"],
                report.get("name", "") + " - " + builder.msg_title,
                True,
            )
            set_complete(report)
            print(f"`{report['name']}` 根据内容判断无需发送.")
            return "根据内容判断该邮件无需投递."
    except Exception as e:
        path = add_err(report["id"], report["name"], format_exc())
        print(f"`{report['name']}` 出现错误 `{repr(e)}` 未发送.")
        return "生成过程出现错误, 已经记录到 %s" % path


def add_err(id_, name, tb):
    path = environ["USERPROFILE"] + "\\DESKTOP\\本地邮件错误%d.txt" % id_
    fp = open(path, "w", encoding="utf-8")
    fp.write(f"{name}:\n\n{tb}")
    fp.close()
    return path


if __name__ == "__main__":
    post_all()
