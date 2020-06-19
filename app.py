import flask
import json

from flask import jsonify, request
from traceback import format_exc
from datetime import datetime
from sys import argv

from post import try_post, get_engine, get_connstr
from post import builder_dict, post_one, get_now_seconds
from robot import add_robot, run_task, dumps, update_task, check_task, get_task
from robot import msgMakers, get_robots_names, get_tasks, extract_msgtxt
import local_mails

LOCAL = "local" in argv
app = flask.Flask(__name__)

if LOCAL:
    print("\n ****** Local Mode ******\n")


@app.route("/")
def index():
    return flask.render_template("index.html", local=LOCAL)


@app.route("/add-access-log", methods=["POST"])
def add_access_log():
    try:
        data = json.loads(request.get_data())
        data["ip"] = request.remote_addr
        sql = "insert into access_log(route,host,ip) values(%s,%s,%s)"
        eng = get_engine()
        params = (data["route"], data["host"], data["ip"])
        eng.execute(sql, params)
        eng.dispose()
        return {"added_log": True}
    except Exception:
        pass


def create_mail_local(mail):
    id_ = local_mails.create(mail)
    return id_


def create_mail_db(mail):
    fields = ["name", "post_time", "receiver", "builder_name", "info", "remarks"]
    maps = map(lambda x: mail[x], fields)
    name, post_time, receiver, builder_name, info, remarks = tuple(maps)
    info = json.dumps(info, ensure_ascii=False)
    sql = (
        "insert into "
        "reports(name,post_time,receiver,builder_name,info,remarks) "
        "values(%s,%s,%s,%s,%s,%s) "
    )
    eng = get_engine()
    params = (name, post_time, receiver, builder_name, info, remarks)
    eng.execute(sql, params)
    id_ = eng.execute("SELECT LAST_INSERT_ID();").fetchall()[0][0]
    eng.dispose()
    return id_


@app.route("/create", methods=["POST"])
def create_mail():
    try:
        mail = json.loads(request.get_data())
        if LOCAL:
            id_ = create_mail_local(mail)
        else:
            id_ = create_mail_db(mail)
        return jsonify({"response": "邮件报表已创建.", "id": id_})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/database-set")
def read_db_set():
    """读取数据库信息, 返回数据库名对应表名的字典"""
    try:
        sql = """SELECT TABLE_SCHEMA,TABLE_NAME
                FROM information_schema.`TABLES`
                WHERE TABLE_SCHEMA not in ('mysql', 'information_schema',
                                            'performance_schema', 'sys')"""
        eng = get_engine()
        items = eng.execute(sql).fetchall()
        result = {}
        for db, table in items:
            if db not in result:
                result[db] = []
            result[db].append(table)
        eng.dispose()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/get-cols/<db>/<table>")
def read_cols(db, table):
    """读取一个表的所有列名"""
    try:
        sql = (
            "select column_name as col "
            "from information_schema.columns "
            "where table_schema = %s and table_name = %s order by col "
        )
        eng = get_engine()
        items = eng.execute(sql, (db, table)).fetchall()
        items = [x[0] for x in items]
        eng.dispose()
        return jsonify({db + table: items})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


def read_mails_local():
    mails = local_mails.get_mails()
    columns = [
        "id",
        "name",
        "post_time",
        "post_weekday",
        "post_day",
        "receiver",
        "complete_time",
        "remarks",
        "builder_name",
        "info",
        "creator",
    ]
    values = []
    for m in mails:
        x = []
        for c in columns:
            x.append(m.get(c))
        values.append(x)
    return columns, values


def read_mails_db():
    sql = (
        "SELECT id,name,post_time,post_weekday,post_day,receiver,"
        "       complete_time,remarks,builder_name,info,creator "
        "  FROM reports where delete_time is null;"
    )
    eng = get_engine()
    items = eng.execute(sql)
    result = [list(i) for i in items.fetchall()]
    eng.dispose()
    return items.keys(), result


@app.route("/mail-list")
def read_mails():
    """读取已经创建的所有邮件列表"""
    try:
        if LOCAL:
            result = read_mails_local()
        else:
            result = read_mails_db()
        return jsonify({"columns": result[0], "values": result[1]})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


def update_mail_local(mail):
    local_mails.update(mail)
    return jsonify({"response": "已修改."})


def update_mail_db(mail):
    mail["info"] = json.dumps(mail["info"], ensure_ascii=False)
    sql = (
        "update reports set name = %s, post_time = %s, "
        "post_weekday= %s, post_day = %s, receiver = %s, "
        "info = %s, remarks = %s, creator = %s where id = %s"
    )
    eng = get_engine()
    eng.execute(
        sql,
        (
            mail["name"],
            mail["post_time"],
            mail["post_weekday"],
            mail["post_day"],
            mail["receiver"],
            mail["info"],
            mail["remarks"],
            mail["creator"],
            mail["id"],
        ),
    )
    return jsonify({"response": "已修改."})


@app.route("/update", methods=["POST"])
def update_mail():
    """修改一个邮件报表的信息"""
    try:
        mail = json.loads(request.get_data())
        if LOCAL:
            return update_mail_local(mail)
        else:
            return update_mail_db(mail)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


def delete_mail_local(id_):
    id_ = int(id_)
    count = local_mails.delete(id_)
    return jsonify({"response": "%d个报表已删除." % count})


def delete_mail_db(id_):
    sql = "update reports set delete_time = now() where id = %s"
    eng = get_engine()
    deletes = eng.execute(sql, (id_))
    return jsonify({"response": "%d个报表已删除." % deletes.rowcount})


@app.route("/delete/<id_>", methods=["POST"])
def delete_mail(id_):
    """删除对应 id 的邮件报表"""
    try:
        if LOCAL:
            return delete_mail_local(id_)
        else:
            return delete_mail_db(id_)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/try-post", methods=["POST"])
def try_post_mail():
    """ajax 指令进行邮件的投递"""
    data = json.loads(request.get_data())
    receiver = data["receiver"]
    key = data["builder_name"]
    info = data["info"]
    info["attach_name"] = data["name"]
    result = try_post(receiver, key, info)
    return jsonify({"response": result})


@app.route("/post-now", methods=["POST"])
def post_now():
    """立刻对邮件进行投递"""
    mail = json.loads(request.get_data())
    if LOCAL:
        result = local_mails.post_one(mail)
        time = get_now_seconds()
        return jsonify({"response": result, "time": time})
    else:
        ip = request.remote_addr
        result = post_one(mail, ip)
        time = get_now_seconds()
        return jsonify({"response": result, "time": time})


@app.route("/check-html", methods=["POST"])
def check_html():
    """返回一个新页面, 显示 builder 的 make_html 方法生成的内容"""
    try:
        data = json.loads(request.get_data())
        key = data["builder_name"]
        info = data["info"]
        connstr = get_connstr()
        builder = builder_dict[key](info, connstr)
        builder.read_data()
        html = builder.make_html()
        return jsonify({"html": html})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/check-sql", methods=["POST"])
def check_sql():
    """检查邮件报表sql生成函数生成的 sql"""
    try:
        data = json.loads(request.get_data())
        key = data["builder_name"]
        info = data["info"]
        func = data["func"]
        args = data["args"]
        connstr = get_connstr()
        builder = builder_dict[key](info, connstr)
        if args == "":
            sql = getattr(builder, func)()
        else:
            args = args.split(",")
            sql = getattr(builder, func)(*args)
        return {"sql": sql}
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/get-info-template/<key>")
def get_info_template(key):
    """根据一个 builder 的 key 获取创建该 builder 所需要的信息"""
    try:
        result = builder_dict[key]
        sql_funcs = [x for x in dir(result) if "make_" in x and "_sql" in x]
        dic = json.loads(result.__doc__)
        dic["sqlFuncs"] = sql_funcs
        return jsonify(dic)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/get-builder-list")
def get_builder_list():
    """"从 post 模块的 builder_dict 中获取当前已有的 builder 的 key"""
    try:
        keys = list(builder_dict.keys())
        return jsonify(keys)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-tasks")
def robot_index():
    """机器人管理页面的页面渲染"""
    try:
        return flask.render_template("robot.html")
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-add-robot", methods=["POST"])
def robot_add_robot():
    """添加一个机器人"""
    try:
        robot = json.loads(request.get_data())
        add_robot(robot)
        return {"response": "%s added." % robot["name"]}
    except Exception as e:
        return {"error": repr(e), "tb": format_exc()}


@app.route("/robot-task-test", methods=["POST"])
def robot_test():
    """测试一个机器人"""
    try:
        task = json.loads(request.get_data())
        result = run_task(task, test=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-task-now", methods=["POST"])
def robot_run_now():
    """立即执行一个任务"""
    try:
        task = json.loads(request.get_data())
        result = run_task(task, force=True)
        result["task"] = task
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-read-tasks")
def robot_tasks():
    """获取所有未删除的任务"""
    try:
        tasks = get_tasks(all=True)
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


def make_now_str():
    return str(datetime.now())[:-7]


@app.route("/robot-add-task", methods=["POST"])
def robot_add_task():
    """添加一个机器人任务"""
    try:
        task = json.loads(request.get_data())
        task["updateTime"] = make_now_str()
        check_task(task)
        if "id" in task:
            del task["id"]
        sql = "insert into jy_mail.robot_tasks(task) values(%s)"
        eng = get_engine()
        eng.execute(sql, (dumps(task)))
        Id = eng.execute("SELECT LAST_INSERT_ID();").fetchall()[0][0]
        return jsonify({"response": "任务已创建.", "id": Id})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-update-tasks", methods=["POST"])
def robot_update_task():
    """更新一个机器人任务"""
    try:
        task = json.loads(request.get_data())
        task["updateTime"] = make_now_str()
        keet_last_status(task)
        check_task(task)
        update_task(task)
        return jsonify({"response": "修改成功."})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-delete-task", methods=["POST"])
def robot_delete_task():
    """删除一个机器人任务"""
    try:
        task = json.loads(request.get_data())
        task["updateTime"] = make_now_str()
        keet_last_status(task)
        task["active"] = "deleted"
        update_task(task)
        return jsonify({"response": "已删除该任务"})
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


def keet_last_status(task):
    old = get_task(task["id"])
    for last in ["lastOperateTs", "lastOperateStatus", "lastSendTs"]:
        task[last] = old[last]


@app.route("/robot-get-template/<key>")
def robot_maker_template(key):
    """一个生成器的模板信息"""
    try:
        maker = msgMakers[key]
        return jsonify(maker.inputs())
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-get-msgmakers")
def robot_msgmakers():
    """返回消息生成器的列表"""
    try:
        keys = list(msgMakers.keys())
        return jsonify(keys)
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-check-msg", methods=["POST"])
def robot_check_msg():
    """检查消息生成器生成的内容文本"""
    try:
        task = json.loads(request.get_data())
        maker = msgMakers[task["msgMaker"]](task["taskInfo"])
        msg = extract_msgtxt(maker.make_msg())
        return jsonify({"text": msg})
    except Exception as e:
        return {"error": repr(e), "tb": format_exc()}


@app.route("/robot-get-robots")
def robot_names():
    """返回消息生成器的列表"""
    try:
        return jsonify(get_robots_names())
    except Exception as e:
        return jsonify({"error": repr(e), "tb": format_exc()})


@app.route("/robot-msg-history", methods=["POST"])
def robot_msg_history():
    """根据机器人名称和任务id查询最近的100条发送记录"""
    try:
        task = json.loads(request.get_data())
        sql = (
            "select robot, dt, said from robot_said "
            "where task_id = %s order by dt desc limit 100"
        )
        eng = get_engine()
        result = eng.execute(sql, task["id"])
        eng.dispose()
        values = [list(i) for i in result.fetchall()]
        for v in values:
            v[1] = str(v[1])
        return jsonify(values)
    except Exception as e:
        return {"error": repr(e), "tb": format_exc()}


if __name__ == "__main__":
    app.run("0.0.0.0", 11496)
