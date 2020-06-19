"""
机器人信息的格式
{
    "active": str 是否在激活状态中
    "at" : str 该任务需要 at 的人
    "creator" : str 创建者
    "days" : list 每月几号运行该任务
    "lastOperateTs" : int 最后一次运行的时间
    "lastOperateStatus" : str 最后一次执行的状态
    "lastSendTs" : int 最后一次发送消息的时间
    "msgMaker" : str 使用的消息模板
    "muteSeconds" : int 每次运行后隔多久再运行
    "name" : str 网页上的名字
    "operateTimes" : []  运行信息, 空列表则每次都运行, 指定时间需要指定
                      { time : int 每日第几秒运行,
                        completeTs : int 完成的时间戳,
                        status : str 几个状态的枚举
                            "current", "ready", "abandon", "empty", "sended"}
    "robot" : str 使用哪个机器人进行发送
    "taskInfo" : dict 本次任务的一些相关信息
    "weekdays" : list 周几运行该任务
    "updateTime" : str 最后一次人工修改/创建/删除的时间
}

机器人任务执行流:

检验时间是否在6:00到23:00 → 不在则直接退出
    ↓
get_tasks() 获取任务列表 → 失败则添加日志, 并返回空字典
    ↓
run_task() 遍历任务
    ↓
set_opt_status_before_run ()
如果任务最后一次执行是昨天, 设置所有的 opt_time.status 为 "ready"
    ↓
in_time_range() 判断任务是否在发送的时间范围内 → 不在时间范围内则返回
    日期是否符合
    星期是否符合
    当前时间已经大于最后运行时间 + 沉默时间
    如果设置了运行时间, 当前时间是否已经超过指定运行时间 3600秒
    ↓
run_task_simple() 获取响应, 消息内容  ->  响应文本不是 ok, 则添加错误日志
    ↓
set_opt_time_after_run() 设置 opt_time 的信息
    last_opt_ts 设置为时间戳
    last_opt_status 为发送状态
    opt_time.status 是 "current" 的设置 status 和对应时间戳
    ↓
update_task() 更新 task 的运行状态
add_msg_log() 添加发送了的消息的记录
"""

from post import get_engine, json, datetime, get_now_seconds
from post import add_local_errlog, add_db_errlog, format_exc, scan_err
from msgMakers import msgMakers
from dingdingRobot import broadcast, ROBOTS, read_json, environ
from copy import copy
import re

ROBOT_ERROR_LOG = r"\Documents\auto_message_maneger\robot_err.json"


def check_task(task):
    """校验任务,删除多余信息"""
    types = {
        "id": int,
        "active": str,
        "at": str,
        "creator": str,
        "days": list,
        "lastOperateTs": int,
        "lastOperateStatus": str,
        "lastSendTs": int,
        "msgMaker": str,
        "muteSeconds": int,
        "name": str,
        "operateTimes": list,
        "robot": str,
        "taskInfo": dict,
        "weekdays": list,
        "updateTime": str,
    }
    for k in types:
        t = types[k]
        assert isinstance(task[k], t), "%s is not %s" % (k, str(t))

    delete = []
    for k in task:
        if k not in types:
            delete.append(k)

    for k in delete:
        del task[k]

    opt_types = {"time": int, "completeTs": int, "status": str}

    for t in task["operateTimes"]:
        delete = []

        for k in t:
            if k not in opt_types:
                delete.append(k)

        for k in delete:
            del t[k]

        for k in opt_types:
            _type = opt_types[k]
            assert isinstance(t[k], _type), "%s is not %s" % (k, _type)


def parse_at(txt):
    """分析需@的列表"""
    return re.findall(r"\d{11}", txt)


def dumps(obj):
    """json.dumps的封装,指定了不编码为ascii,对键进行排序"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def extract_msgtxt(msg):
    """提取消息的text"""
    if msg.get("empty", False) is True:
        return "空消息,不发送."
    if msg["msgtype"] == "text":
        return msg["text"]["content"]
    if msg["msgtype"] == "markdown":
        return msg["markdown"]["text"]
    if msg["msgtype"] == "feedCard":
        links = msg["feedCard"]["links"]
        links = map(lambda x: str(x), links)
        return "\n".join(links)


def get_robots_names():
    """获取所有机器人的名称"""
    path = environ["USERPROFILE"] + ROBOTS
    robots = read_json(path)
    return list(robots.keys())


def add_robot(robot):
    """添加一个机器人"""
    path = environ["USERPROFILE"] + ROBOTS
    robot = copy(robot)
    robots = read_json(path)
    name = robot["name"]
    if name in robots:
        raise NameError("机器人 %s 已存在." % name)
    del robot["name"]
    robots[name] = robot
    fp = open(path, "w", encoding="utf-8")
    json.dump(robots, fp, ensure_ascii=False)
    fp.close()
    return "%s added." % name


def get_timestamp():
    """当前的时间戳, int类型, 单位为秒"""
    d = datetime.datetime.now()
    return int(d.timestamp())


def get_dayinfo():
    """今天是本月的第几天, 星期几"""
    d = datetime.datetime.now()
    return d.day, d.weekday() + 1


def get_tasks(all=False):
    """从数据库中查询基本符合要求的任务"""
    try:
        eng = get_engine()

        if all:
            sql = (
                "select id,task from auto_message_maneger.robot_tasks "
                " where (task -> '$.active') <> 'deleted'"
            )
            result = eng.execute(sql)
        else:
            ts = get_timestamp()
            sql = (
                "select id,task from auto_message_maneger.robot_tasks \n"
                "where (task -> '$.lastSendTs' + task -> '$.muteSeconds') < %s"
                "  and (task -> '$.active') = 'active'"
            )
            result = eng.execute(sql, ts)

        tasks = []
        for _id, _task in result.fetchall():
            task = json.loads(_task)
            task["id"] = _id
            tasks.append(task)
        eng.dispose()
        return tasks
    except Exception:
        add_local_errlog(format_exc(), path=ROBOT_ERROR_LOG)
        return []


def get_task(tid):
    try:
        sql = "select id,task from auto_message_maneger.robot_tasks where id = %s"
        eng = get_engine()
        result = eng.execute(sql, (tid))
        eng.dispose()
        for _id, _task in result.fetchall():
            task = json.loads(_task)
            task["id"] = _id
            return task
    except Exception:
        raise KeyError("未查找到id为%d的任务." % tid)


def update_task(task):
    """把当前 task 的信息更新到数据库"""
    task = copy(task)
    task_id = task["id"]
    del task["id"]
    sql = "update auto_message_maneger.robot_tasks set task = %s where id = %s"
    eng = get_engine()
    eng.execute(sql, (dumps(task), task_id))
    eng.dispose()


def get_msg(task):
    """
    获取 task 生成的消息
    """
    maker_name = task["msgMaker"]
    info = task["taskInfo"]
    maker = msgMakers[maker_name](info)
    maker.assert_before_make()
    return maker.make_msg()


def run_task(task, force=False, test=False):
    """运行一个任务的全流程"""
    try:
        if not test:
            set_opt_status_before_run(task)
            if not force and not in_time_range(task):
                return {"response": "当前的时间不需要发送消息.", "text": ""}

        msg = get_msg(task)  # 这里如果出错一定会抛出异常
        at = parse_at(task["at"])
        responses = []

        # 这个循环出错如果是机器人消息错误, 基本不会抛出异常
        for robot in task["robot"].split(","):
            if msg.get("empty", False) is True:
                response = {"errmsg": "空消息,未发送.", "errcode": 0}
            else:
                response = broadcast(robot, "", msg, at=at)
            response["robot"] = robot
            responses.append(response)
            if response.get("errcode", 0) != 0:
                if not test:  # 因为不会抛出异常, 所以非测试情况下直接添加错误
                    t = (robot, task["id"], response["errmsg"])
                    err = "%s\n%d\n%s\n" % t
                    add_db_errlog(err, table="robot_err_logs")
                    add_local_errlog(err, creator=task["creator"], path=ROBOT_ERROR_LOG)
            else:
                add_msg_log(robot, task["id"], msg, test)

        response = get_response_from_set(responses)

        if not test:
            task = set_opt_time_after_run(task, msg.get("empty", False))
            update_task(task)
        return {"response": dumps(response), "text": extract_msgtxt(msg)}
    except Exception as e:
        if not test:
            err = {"id": task["id"], "task": task["name"], "tb": format_exc()}
            err = dumps(err)
            add_local_errlog(err, creator=task["creator"], path=ROBOT_ERROR_LOG)
            add_db_errlog(err, "robot_err_logs")
        return {"error": repr(e), "tb": format_exc()}


def get_response_from_set(responses):
    """从响应集合中生成给页面返回的响应"""
    assert len(responses) > 0, "响应集合为空"
    result = {}
    for err in responses:
        k = err["robot"]
        v = err["errmsg"]
        result[k] = v
    return result


def set_opt_status_before_run(task):
    """如果最后一次运行是昨天, 则重设所有运行状态为 ready"""
    d = datetime.date.today()
    ts = datetime.datetime.fromisoformat(str(d)).timestamp()
    if task["lastOperateTs"] < ts:
        for x in task["operateTimes"]:
            x["status"] = "ready"


def in_time_range(task):
    """消息是否需要发送"""
    result = False
    ts = get_timestamp()
    ti = get_now_seconds()
    day, wkday = get_dayinfo()

    if len(task["days"]) > 0 and day not in task["days"]:
        return False

    if len(task["weekdays"]) > 0 and wkday not in task["weekdays"]:
        return False

    if ts < task["lastOperateTs"] + task["muteSeconds"]:
        return False

    if len(task["operateTimes"]) == 0:
        return True

    for x in task["operateTimes"][::-1]:
        if x["status"] == "ready" and 0 <= ti - x["time"] < 3600:
            x["status"] = "current"
            return True

    return result


def set_opt_time_after_run(task, is_empty):
    """
    在运行任务后设置状态信息

    首先设置 task 的 lastOperateTs, lastOperateStatus, lastSendTs

    然后遍历小于当前时间的所有 operateTimes

    operateTimes.status = 'ready' 则 更改为 abandon

    operateTimes.status = 'current' 则 更改为 "sended" 或者 "empty"
    """
    if is_empty:
        status = "empty"
    else:
        status = "sended"
        task["lastSendTs"] = get_timestamp()

    task["lastOperateTs"] = get_timestamp()
    task["lastOperateStatus"] = status

    if len(task["operateTimes"]) == 0:
        return

    ti = get_now_seconds()
    for x in task["operateTimes"]:
        if x["time"] <= ti:
            if x["status"] == "current":
                x["status"] = status
                x["completeTs"] = get_timestamp()
            if x["status"] == "ready":
                x["status"] = "abandon"
    return task


def add_msg_log(robot, task_id, msg, test=False):
    txt = extract_msgtxt(msg)
    if test:
        txt = "[TEST]" + txt
    sql = "insert into auto_message_maneger.robot_said(robot,task_id,said) values(%s,%s,%s)"
    eng = get_engine()
    eng.execute(sql, (robot, task_id, txt))
    eng.dispose()


def main():

    # 23:00 到 6:00 不发送消息
    now = datetime.datetime.now()
    if now.hour < 6 or now.hour > 23:
        return

    tasks = get_tasks()
    for task in tasks:
        run_task(task)
    scan_err(ROBOT_ERROR_LOG)


if __name__ == "__main__":
    main()
