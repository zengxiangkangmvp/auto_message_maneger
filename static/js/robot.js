"use strict";

// 清洗列表
function cleanText(arraytext) {
    arraytext
        .replace(/，/g, ",")
        .split(",")
        .map(e => e.trim())
        .filter(e => e != "")
        .join(",");
    return arraytext;
}

var Inputs = {
    get infoInputs() {
        return $("#info-inputs input");
    },

    get robotText() {
        return $("#task-robot").val();
    },

    get taskRobot() {
        let robots = $("#task-robot").val()
            .split(",")
            .filter(e => panel.robotList.indexOf(e) > -1);
        robots = Array.from(new Set(robots));
        return robots.join(",");
    },

    set taskRobot(val) {
        return $("#task-robot").val(val);
    },

    get taskId() {
        return parseInt($("#task-id").text());
    },

    set taskId(val) {
        return $("#task-id").text(val);
    },

    get taskName() {
        return $("#task-name").val();
    },

    set taskName(val) {
        return $("#task-name").val(val);
    },

    get taskMsgMaker() {
        return $("#task-msgMaker").val();
    },

    set taskMsgMaker(val) {
        return $("#task-msgMaker").val(val);
    },

    get taskDatabase() {
        return $("#task-database").val();
    },

    set taskDatabase(val) {
        return $("#task-database").val(val);
    },

    get taskTable() {
        return $("#task-table").val();
    },

    set taskTable(val) {
        return $("#task-table").val(val);
    },

    get taskWeekdays() {
        return cleanText($("#task-weekdays").val())
            .split(",")
            .map(e => parseInt(e))
            .filter(e => !isNaN(e));
    },

    set taskWeekdays(val) {
        return $("#task-weekdays").val(val.join(","));
    },

    get taskDays() {
        return cleanText($("#task-days").val())
            .split(",")
            .map(e => parseInt(e))
            .filter(e => !isNaN(e));
    },

    set taskDays(val) {
        return $("#task-days").val(val.join(","));
    },

    get taskAt() {
        return cleanText($("#task-at").val().replace(/\n/g, ","));
    },

    set taskAt(val) {
        return $("#task-at").val(val.replace(/,/g, "\n"));
    },

    get taskMuteSeconds() {
        let i = parseInt($("#task-mute").val());
        return isNaN(i) ? 0 : i;
    },

    set taskMuteSeconds(val) {
        $("#task-mute").val(val);
    },

    get taskTestSql() {
        return document.getElementById("task-testSql").value.trim();
    },

    set taskTestSql(val) {
        document.getElementById("task-testSql").value = val;
    },

    get taskCreator() {
        return $("#task-creator").val();
    },

    set taskCreator(val) {
        return $("#task-creator").val(val);
    },

    get taskOperateTimes() {
        return $("#task-opt-time").val();
    },

    set taskOperateTimes(val) {
        let array = val.map(e => timeconverter(e["time"]));
        return $("#task-opt-time").val(array.join(","));
    }

};

class Panel {
    constructor() {
        this.makerList = [];  // 目前所有支持的报表生成器列表
        this.robotList = [];  // 目前所有的机器人列表
        this.currentInfoTemplate = {};  // 当前页面所使用的生成器的 info模板 的 dict
        this.taskList = []; // 数据库已经有的邮件报表
        this.databaseSet = []; // 当前服务器中所有的数据库以及数据表的字典集合
        this.actions = [];
        this.allowChange = true;  // 是否可以切换任务信息
    }

    // 当前的任务
    get currentTask() {
        let task = {
            id: Inputs.taskId,
            active: "active",
            at: this.taskAt,
            creator: Inputs.taskCreator,
            days: Inputs.taskDays,
            lastOperateTs: -1,
            lastOperateStatus: "ready",
            lastSendTs: -1,
            msgMaker: Inputs.taskMsgMaker,
            muteSeconds: Inputs.taskMuteSeconds,
            name: Inputs.taskName,
            operateTimes: this.taskOptTime,
            robot: Inputs.taskRobot,
            taskInfo: this.taskInfo,
            updateTime: new Date().toLocaleString(),
            weekdays: Inputs.taskWeekdays,
        };

        let existTask = this.taskList.find(e => e["id"] == task["id"]);
        if (existTask != undefined) {
            ["lastOperateTs", "lastOperateStatus", "lastSendTs", "updateTime"].forEach(e => {
                task[e] = existTask[e];
            });
        }

        return task;
    }

    // 获取任务的运行信息
    get taskInfo() {
        let result = {
            database: Inputs.taskDatabase,
            table: Inputs.taskTable
        };
        if (Inputs.taskTestSql != "") {
            result["testSql"] = Inputs.taskTestSql;
        }
        Inputs.infoInputs.each(function () {
            let v = getVal($(this)[0]);
            let k = $(this)[0].name;
            if (v !== "") {
                result[k] = v;
            }
        });
        $("#info-inputs select").each(function () {
            let v = getVal($(this)[0]);
            let k = $(this)[0].name;
            if (v !== "") {
                result[k] = v;
            }
        });
        return result;
    }

    // 获取任务的运行时间
    get taskOptTime() {
        let txt = Inputs.taskOperateTimes;
        let id = Inputs.taskId;
        let existTask = this.taskList.find(e => e["id"] == id);
        txt = cleanText(txt);
        let times = txt.split(",").map(e => {
            let old = undefined;
            if (existTask != undefined) {
                old = existTask.operateTimes.find(x => x["time"] == timeconverter(e));
            }
            if (old != undefined) {
                return old;
            } else {
                return {
                    time: timeconverter(e),
                    completeTs: -1,
                    status: "ready"
                };
            }
        });
        times = times.filter(e => !isNaN(e["time"]));
        return times;
    }

    // 设置任务的运行时间
    set taskOptTime(val) {
        Inputs.taskOperateTimes = val;
    }

    // 任务需要 at 的列表
    get taskAt() {
        return Inputs.taskAt;
    }

    // 设置任务需要 at 的列表
    set taskAt(val) {
        Inputs.taskAt = val;
    }

    // 修改右下角的进度文本信息
    set progress(val) {
        this.actions.push([new Date(), val]);
        $("#progress").text(val);
    }

    // 展示机器人任务列表
    showTasks() {
        $('#actions-list').hide();
        $('#tasks-table').show();
        $(".tabs").children().toggleClass("active", false);
        $("#tasks-tab").toggleClass("active", true);
    }

    // 展示操作记录
    showActions() {
        $('#tasks-table').hide();
        panel.renderActionList();
        $('#actions-list').show();
        $(".tabs").children().toggleClass("active", false);
        $("#actions-tab").toggleClass("active", true);
    }

    // 渲染可选的 database option 元素
    renderDatabaseOptions() {
        let dbSet = Object.keys(panel.databaseSet);
        setSelectOptions("task-database", dbSet);
    }

    // 渲染机器人的 option 元素
    renderRobotsOptions() {
        $("#ready-robots").children().remove();
        let current = Inputs.robotText.split(",").slice(-1)[0];
        let robots = this.robotList.filter(robot => current == "" ? true : robot.indexOf(current) > -1);
        robots.forEach(r => {
            let div = document.createElement("div");
            div.innerText = r;
            div.addEventListener("click", function () {
                let selected = $(this).text();
                let array = Inputs.taskRobot.split(",");
                array.push(selected);
                array = Array.from(new Set(array)).filter(e => panel.robotList.indexOf(e) > -1);
                Inputs.taskRobot = array.join(",");
            });
            $("#ready-robots").append(div);
        });

    }

    // 渲染可选的 table option 元素
    renderTableOptions() {
        let k = Inputs.taskDatabase;
        let tables = panel.databaseSet[k];
        setSelectOptions("task-table", tables);
    }

    // 渲染可选的 maker option 元素
    renderMakerOptions() {
        setSelectOptions("task-msgMaker", panel.makerList);
    }

    // 创建消息类型的模板输入控件
    renderInfoInputs() {
        $("#info-inputs").children().remove();
        let items = this.infoTemplate;
        items.forEach(i => { panel.renderInfoInput(i); });
    }

    // 渲染任务列表
    renderTasksTable() {
        $("#tasks-tbody").children().remove();
        let filterBy = $("#filter-by").val();
        let tasks = this.taskList.filter(e => {
            if (filterBy.trim() == "") {
                return true;
            } else {
                return e["name"].indexOf(filterBy) > -1 || e["robot"].indexOf(filterBy) > -1 || e["creator"].indexOf(filterBy) > -1;
            }
        });

        let funcdict = {
            "名称顺序": (a, b) => a["name"] < b["name"] ? -1 : 1,
            "机器人顺序": (a, b) => a["robot"] < b["robot"] ? -1 : 1,
            "创建时间顺序": (a, b) => a["id"] < b["id"] ? -1 : 1,
            "创建时间逆序": (a, b) => a["id"] > b["id"] ? -1 : 1,
        };

        let func = funcdict[$("#sort-by").val()];
        tasks.sort(func);

        tasks.forEach(t => {
            let tr = document.createElement("tr");
            let fields = ["id", "name", "robot", "optTime", "lastOperate", "creator"];
            fields.forEach(i => {
                let td = document.createElement("td");

                td.innerText = String(t[i]);

                if (i == "robot") {
                    td.setAttribute("title", t["robot"].replace(/,/g, '\n'));
                }

                if (i == "lastOperate") {
                    td.innerText = t["lastOperateTs"] == -1 ? "未运行" : new Date(t["lastOperateTs"] * 1000).toLocaleString() + " (" + t["lastOperateStatus"] + ")";
                }

                if (i == "optTime") {
                    let txt = t["operateTimes"].map(x => timeconverter(x["time"])).join(",");
                    txt = txt == "" ? "随时" : txt;
                    let weekdays = t["weekdays"].join(",");
                    let days = t["days"].join(",");
                    weekdays = weekdays == "" ? "" : " 每周" + weekdays;
                    days = days == "" ? "" : " 每月" + days + "日";
                    td.innerText = txt + weekdays + days;
                }

                tr.append(td);
            });

            tr.addEventListener("click", function () {
                let id = $(this).children().first().text();
                id = parseInt(id);
                if (panel.allowChange) {
                    panel.fillInputs(id);
                }
            });

            document.getElementById("tasks-tbody").append(tr);
        });

        panel.highlightCurrentTask();
    }

    // 根据选中任务填写输入控件
    fillInputs(id) {
        let task = this.taskList.find(e => e["id"] == id);
        let maker = task["msgMaker"];
        Inputs.taskMsgMaker = maker;
        panel.getTaskTemplate().then(() => {
            ["id", "name", "msgMaker", "robot", "weekdays", "days",
                "operateTimes", "at", "muteSeconds", "creator"].forEach(
                    field => {
                        let inputField = "task" + field[0].toUpperCase() + field.slice(1);
                        Inputs[inputField] = task[field];
                    }
                );

            if (task["taskInfo"]["database"] != undefined) {
                Inputs.taskDatabase = task["taskInfo"]["database"];
                panel.renderTableOptions();
                Inputs.taskTable = task["taskInfo"]["table"];
            }
            panel.renderInfoInputs();
            Inputs.infoInputs.each(function () {
                let k = $(this)[0].name;
                if (task.taskInfo.hasOwnProperty(k)) {
                    setVal($(this)[0], task.taskInfo[k]);
                } else {
                    setVal($(this)[0], "");
                }
            });
            panel.highlightCurrentTask();
        });

    }

    // 列表中高亮当前选择的任务
    highlightCurrentTask() {
        let id = Inputs.taskId;
        if (isNaN(id)) {
            return;
        }
        $('tr').css("background-color", "");
        $("tr").each(function () {
            if ($(this).children().first().text() == id) {
                $(this).css("background-color", "#505050");
            }
        });
    }

    // 渲染单个输入控件
    renderInfoInput(item) {
        let group = document.createElement("div");
        group.className = "input-group";
        let span = document.createElement("span");
        span.innerText = item["label"];

        let input = undefined;
        if (item["type"] == "textarea") {
            input = document.createElement("textarea");
        } else {
            input = document.createElement("input");
            input.setAttribute("type", item["type"]);
        }

        input.setAttribute("name", item["name"]);

        if (item.hasOwnProperty("des")) {
            input.setAttribute("title", item["des"]);
        }

        if (item.hasOwnProperty("default")) {
            setVal(input, item["default"]);
        }

        group.append(span);
        group.append(input);
        document.getElementById("info-inputs").append(group);
    }


    // ajax 获取所有机器人名称
    getRobotsNames() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "获取全部机器人中...";
            let url = "/robot-get-robots";
            let callbacks = {
                success: (xhr) => {
                    panel.robotList = xhr;
                    panel.progress == "全部机器人获取完成";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }


    // ajax 获取所有的消息生成器
    getMakerList() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "获取全部消息生成器中...";
            let url = "/robot-get-msgmakers";
            let callbacks = {
                success: (xhr) => {
                    panel.makerList = xhr;
                    panel.progress = "全部消息生成器获取完成";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 获取当前任务类型的 info
    getTaskTemplate() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "获取消息模板信息...";
            let url = "/robot-get-template/" + Inputs.taskMsgMaker;
            let callbacks = {
                success: (xhr) => {
                    panel.infoTemplate = xhr;
                    panel.progress = "全部消息模板输入控件获取完成";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 执行读取数据以及数据表
    readDbSet() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "数据库以及数据表信息读取中...";
            let url = "/database-set";
            let callbacks = {
                success: (xhr) => {
                    panel.databaseSet = xhr;
                    panel.progress = "全部数据表信息获取完毕.";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 读取任务列表
    readTasks() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "全部任务信息读取中...";
            let url = "/robot-read-tasks";
            let callbacks = {
                success: xhr => {
                    panel.taskList = xhr;
                    panel.renderTasksTable();
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 创建任务
    creatTask() {
        let promise = new Promise(function (resolve, reject) {
            if (!panel.checkTask()) {
                reject();
                return;
            }
            panel.progress = "创建请求发送中...";
            let url = "/robot-add-task";
            let task = panel.currentTask;
            task["lastSendTs"] = -1;
            task["lastOperateStatus"] = "ready";
            task["lastOperateTs"] = -1;
            task["operateTimes"].forEach(x => {
                x["completeTs"] = -1;
                x["status"] = "ready";
            });
            task["id"] = -1;
            let callbacks = {
                success: (xhr) => {
                    task["id"] = xhr["id"];
                    panel.taskList.push(task);
                    panel.renderTasksTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 更新任务
    updateTask() {
        if (isNaN(Inputs.taskId)) {
            return this.creatTask();
        }

        let promise = new Promise(function (resolve, reject) {
            if (!confirm('确定修改吗?')) {
                reject();
                return;
            }
            let url = "/robot-update-tasks";
            let task = panel.currentTask;
            let callbacks = {
                success: (xhr) => {
                    let i = panel.taskList.findIndex(e => e["id"] == task.id);
                    panel.taskList[i] = task;
                    panel.renderTasksTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            panel.progress = "修改信息发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 执行删除操作
    deleteTask() {
        let promise = new Promise(function (resolve, reject) {
            if (!confirm('确定删除该任务吗?')) {
                reject();
                return;
            }
            if (isNaN(Inputs.taskId)) {
                panel.progress = "当前无选中的任务.";
                reject();
                return;
            }

            let task = panel.currentTask;
            let url = "/robot-delete-task";
            let callbacks = {
                success: (xhr) => {
                    panel.taskList = panel.taskList.filter(e => e["id"] != task["id"]);
                    panel.renderTasksTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            panel.progress = "删除请求发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 指令立即执行任务
    runTaskNow() {
        let promise = new Promise(function (resolve, reject) {
            if (!confirm('确定立即执行该任务吗? 任务会被保存, 对应机器人将会发出一条消息')) {
                reject();
                return;
            }
            let url = "/robot-task-now";
            let task = panel.currentTask;
            let callbacks = {
                success: (xhr) => {
                    let task = xhr["task"];
                    let i = panel.taskList.findIndex(e => e["id"] == task.id);
                    panel.taskList[i] = task;
                    panel.progress = "发送状态:" + xhr["response"];
                    panel.renderTasksTable();
                    alert("已经发送的内容: \n\n" + xhr["text"]);
                }
            };
            panel.progress = "任务执行中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 运行一条测试任务, 仅发送消息, 不添加日志
    runTaskTest() {
        let promise = new Promise(function (resolve, reject) {
            if (!confirm('确定测试该任务吗? 对应的机器人将会发出一条消息.')) {
                reject();
                return;
            }
            let url = "/robot-task-test";
            let task = panel.currentTask;
            let callbacks = {
                success: (xhr) => {
                    panel.progress = "发送状态:" + xhr["response"];
                    alert(xhr["text"]);
                }
            };
            panel.progress = "测试任务执行中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 在服务端生成一条消息, 查看消息的内容
    checkMsg() {
        let promise = new Promise(function (resolve, reject) {
            let url = "/robot-check-msg";
            let task = panel.currentTask;
            let callbacks = {
                success: (xhr) => {
                    panel.progress = "消息已生成并弹出.";
                    alert(xhr["text"]);
                }
            };
            panel.progress = "消息生成中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 查看消息发送的最近100条记录
    getMsgHistory() {
        let promise = new Promise(function (resolve, reject) {
            let url = "/robot-msg-history";
            let task = {
                id: panel.currentTask.id
            };
            let callbacks = {
                success: (xhr) => {
                    xhr.forEach(log => {
                        myWindow.document.write(["<pre>", log[0], " ", log[1], ":\n\n", log[2], "\n</pre><hr />"].join(""));
                    });
                    myWindow.focus();
                }
            };
            let myWindow = window.open('', '', 'width=720,height=480');
            panel.progress = "历史记录查询中...";
            getJSON(url, callbacks, resolve, reject, "POST", task);
        });
        return promise;
    }

    // ajax 添加一个机器人
    addRobot() {
        let robot = {
            "name": $("#new-robot-name").val().trim(),
            "api": $("#new-robot-api").val().trim(),
            "key": $("#new-robot-key").val().trim()
        };
        let promise = new Promise(function (resolve, reject) {
            if (robot["name"] == "" || robot["api"] == "" || robot["key"] == "") {
                panel.progress = "机器人信息未填写完整.";
                reject();
            }
            let url = "/robot-add-robot";
            let callbacks = {
                success: (xhr) => {
                    panel.robotList.push(robot["name"]);
                    panel.progress = xhr["response"];
                }
            };
            panel.progress = "机器人添加中...";
            getJSON(url, callbacks, resolve, reject, "POST", robot);
        });
        return promise;
    }

    // 检查 task 是否合法
    checkTask() {
        let task = panel.currentTask;
        if (task["name"] == "") {
            panel.progress = "未填写任务名称";
            return false;
        }
        if (typeof task["muteSeconds"] != "number") {
            panel.progress = "暂停时长非有效数字";
        }
        if (task["creator"] == "") {
            panel.progress = "未填写创建人";
            return false;
        }
        if (task["robot"] == "" || task["robot"] == null) {
            panel.progress = "未选择机器人";
            return false;
        }
        return true;
    }

    // 渲染操作记录的表格
    renderActionList() {
        $("#actions-list").children().remove();
        this.actions.slice(-30).forEach(row => {
            let li = document.createElement("li");
            li.innerText = row[0].toLocaleTimeString() + " " + row[1];
            document.getElementById("actions-list").append(li);
        });
    }

}

// Panel.prototype.readDbSet = prototypes.readDbSet

var panel = new Panel();

panel.getMakerList()
    .then(() => {
        panel.renderMakerOptions();
        panel.getTaskTemplate().then(() => { panel.renderInfoInputs(); });
    });
panel.readDbSet()
    .then(() => {
        panel.renderDatabaseOptions();
        panel.renderTableOptions();
    });
panel.getRobotsNames()
    .then(() => { panel.renderRobotsOptions(); });
panel.readTasks();