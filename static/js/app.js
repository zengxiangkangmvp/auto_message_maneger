"use strict";

// 格式化发送时间
// 没有指定周或者每月几号的直接返回时间值
// 指定了周或者每月几号的在时间值后面添加周或者每月几号的信息
// 并且根据今天是否所在的周或者每月几号给发送时间添加下划线
function formatPostTime(obj) {
    if (obj["post_weekday"] == "" && obj["post_day"] == "") {
        return obj["post_time"];
    }
    let d = new Date();
    let weekday = d.getDay().toString();
    let day = d.getDate().toString();

    let weekdayText = obj["post_weekday"] == "" ? "" : "周" + obj["post_weekday"];
    let dayText = obj["post_day"] == "" ? "" : "每月" + obj["post_day"] + "日";

    let result = "";
    if (obj["post_weekday"].split(",").indexOf(weekday) == -1 &&
        obj["post_day"].split(",").indexOf(day) == -1) {
        result = "<s>" + obj["post_time"] + "</s>";
    } else {
        result = obj["post_time"];
    }
    result = result + " " + weekdayText + dayText;
    return result;
}

class Panel {
    constructor() {
        this.builderList = [];  // 目前所有支持的报表生成器列表
        this.currentInfoTemplate = {};  // 当前页面所使用的生成器的 info模板 的 dict
        this.mailList = []; // 数据库已经有的邮件报表
        this.databaseSet = []; // 当前服务器中所有的数据库以及数据表的字典集合
        this.actions = [];
        this.allowChange = true;  // 是否可以切换邮件信息
        this.cols = {};  // 表对应的列名信息
        // this.currentReport = {}  // 当前页面正在编辑的 report 信息
    }

    // 当前所使用的报表生成器名字
    get currentBuilder() {
        return $("#report-builder").val();
    }

    set currentBuilder(v) {
        return $("#report-builder").val(v);
    }

    get currentReportId() {
        let id = $("#report-id").text();
        return id == "" ? null : parseInt(id);
    }

    set currentReportId(v) {
        return $("#report-id").text(v);
    }

    // 清洗右侧输入控件面板的星期几或者每月几号发送的文本
    readWeekOrDayStr(target) {
        let v = $(target).val()
            .replace(/，/g, ",")
            .split(",")
            .map(e => e.trim())
            .filter(e => e != "")
            .join(",");
        return v;
    }


    // 当前的报告生成器实例
    get currentReport() {
        let info = this.readInfo();
        let receiver = $("#report-receiver").val()
            .split("\n")
            .map(e => e.trim())
            .filter(e => e != "")
            .join(",")
            .replace(/：/g, ":")
            .replace(/ /g, "");
        let name = $("#report-name").val();
        name = name == "" ? "未命名报表" : name;

        let result = {
            name: name,
            post_time: timeconverter($("#report-post-time").val()),
            post_weekday: this.readWeekOrDayStr("#report-post-weekday"),
            post_day: this.readWeekOrDayStr("#report-post-day"),
            receiver: receiver,
            builder_name: panel.currentBuilder,
            info: info,
            remarks: $("#report-remarks").val(),
            creator: $("#report-creator").val()
        };
        if (this.currentReportId != null) {
            result["id"] = this.currentReportId;
        }
        return result;
    }

    // 修改右下角的进度文本信息
    set progress(val) {
        this.actions.push([new Date(), val]);
        $("#progress").text(val);
    }

    // 清空 info 的控件组
    clearInfoInputs() {
        $("#info-inputs").children().remove();
    }

    // 展示邮件列表
    showMails() {
        $('#actions-list').hide();
        $('#mails-table').show();
        $(".tabs").children().toggleClass("active", false);
        $("#mails-tab").toggleClass("active", true);
    }

    // 展示操作记录
    showActions() {
        $('#mails-table').hide();
        panel.renderActionList();
        $('#actions-list').show();
        $(".tabs").children().toggleClass("active", false);
        $("#actions-tab").toggleClass("active", true);
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

    checkReport() {
        let report = this.currentReport;

        if (report["name"] == "") {
            this.progress = "未填写报表名称";
            return false;
        }
        if (report["receiver"] == "") {
            this.progress = "未填写收件人";
            return false;
        }
        if (report["creator"] == "") {
            this.progress = "未填写创建人";
            return false;
        }
        if (isNaN(report["post_time"])) {
            this.progress = "发送时间";
            return false;
        }

        this.progress = "报表的基本设置已确认全部填写.";
        return true;
    }

    // 在邮件列表中高亮当前右侧面板的邮件
    highlightCurrentReport() {
        if (panel.currentReportId == undefined) {
            return;
        }

        $('tr').css("background-color", "");
        let id = this.currentReportId.toString();
        $("tr").each(function () {
            if ($(this).children().first().text() == id) {
                $(this).css("background-color", "#505050");
            }
        });
    }


    // 渲染当前获取到的邮件的列表
    renderMailsTable() {
        $("#mails-tbody").children().remove();
        let filterBy = $("#filter-by").val();
        let mails = this.mailList.filter(e => {
            if (filterBy.trim() == "") {
                return true;
            } else {
                return e["name"].indexOf(filterBy) > -1 || e["receiver"].indexOf(filterBy) > -1;
            }
        });

        let funcdict = {
            "名称顺序": (a, b) => a["name"] < b["name"] ? -1 : 1,
            "创建时间顺序": (a, b) => a["id"] < b["id"] ? -1 : 1,
            "创建时间逆序": (a, b) => a["id"] > b["id"] ? -1 : 1,
            "发送时间顺序": (a, b) => timeconverter(a["post_time"]) < timeconverter(b["post_time"]) ? -1 : 1,
        };
        let func = funcdict[$("#sort-by").val()];

        mails.sort(func);

        mails.forEach(row => {
            let tr = document.createElement("tr");
            ["id", "name", "post_time", "receiver", "complete_time", "creator"].map((i) => {
                let td = document.createElement("td");
                td.innerText = row[i] || "";

                if (i == "name") {
                    td.setAttribute("title", row["remarks"]);
                }

                if (i == "post_time") {
                    td.innerHTML = formatPostTime(row);
                }

                if (i == "receiver") {
                    td.setAttribute("title", row["receiver"].replace(/,/g, "\n"));
                }

                if (i == "creator") {
                    td.style["max-width"] = "2rem";
                    td.setAttribute("title", row["creator"]);
                }

                tr.append(td);
            });

            tr.addEventListener("click", function () {
                let id = tr.cells[0].innerText;
                if (panel.allowChange) {
                    panel.fillInfoInputs(id);
                }
            });
            document.getElementById("mails-tbody").append(tr);
        });

        panel.highlightCurrentReport();
    }

    // 渲染当前 builder 的 info 控件组
    renderInfoInputs() {
        $("#report-name").val("");
        $("#report-receiver").val("");
        $("#report-remarks").val("");
        $("#report-id").text("");
        panel.clearInfoInputs();
        let items = this.currentInfoTemplate.info;
        let describe = this.currentInfoTemplate.describe;
        let funcs = this.currentInfoTemplate.sqlFuncs;

        let ul = document.createElement("ul");
        ul.className = "col-list";
        document.getElementById("info-inputs").append(ul);
        $("#report-builder").attr("title", describe);
        items.forEach(i => {
            panel.renderInfoInput(i);
        });
        setSelectOptions("sql-funcs", funcs);
    }

    // 渲染单个控件输入框组
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

        input.className = "custom-info";
        input.setAttribute("name", item["name"]);

        input.addEventListener("focusin", function () {
            if (item["name"].indexOf("Col") > -1) {
                panel.activeCol = item["name"];
                $(input).after($(".col-list"));
                $(".col-list").show();
            } else {
                $(".col-list").hide();
            }
        });

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

    // 渲染可选的 builder option 元素
    renderBuilderOptions() {
        setSelectOptions("report-builder", panel.builderList);
    }

    // 渲染可选的 database option 元素
    renderDatabaseOptions() {
        let dbSet = Object.keys(panel.databaseSet);
        setSelectOptions("report-database", dbSet);
    }

    // 渲染可选的 table option 元素
    renderTableOptions() {
        let k = panel.readInfo()["database"];
        let tables = panel.databaseSet[k];
        setSelectOptions("report-table", tables);
    }

    // 根据获取到的实例信息填写 info 的控件, 并对左侧列表中选中项高亮
    fillInfoInputs(id) {
        let mail = this.mailList.find(e => e["id"] == id);
        let builderName = mail["builder_name"];
        panel.currentReportId = id;
        panel.currentBuilder = builderName;
        panel.getInfoTemplate().then(() => {
            panel.renderInfoInputs();
            let info = mail["info"];
            if (document.getElementById("report-local-attach") != null) {
                document.getElementById("report-local-attach").value = info["local_attach"] == undefined ? "" : info["local_attach"];
            }
            $("#report-id").text(mail["id"]);
            $("#report-name").val(mail["name"]);
            $("#report-post-time").val(mail["post_time"]);
            $("#report-post-weekday").val(mail["post_weekday"]);
            $("#report-post-day").val(mail["post_day"]);
            $("#report-receiver").val(mail["receiver"].replace(/,/g, "\n"));
            $("#report-remarks").val(mail["remarks"]);
            $("#report-creator").val(mail["creator"]);
            $("#report-database").val(info["database"]);
            $("#report-testSql").val(info["testSql"]);
            panel.renderTableOptions();
            $("#report-table").val(info["table"]);
            $(".custom-info").each(function () {
                let k = $(this)[0].name;
                if (info.hasOwnProperty(k)) {
                    setVal($(this)[0], info[k]);
                } else {
                    setVal($(this)[0], "");
                }
            });
            panel.readCols().then(() => { panel.renderCols(); });
            panel.highlightCurrentReport();
        });
    }

    // 获取报表生成的 builder 信息
    readInfo() {
        let result = {
            database: document.querySelector("#report-database").value,
            table: document.querySelector("#report-table").value,
        };

        let testSql = document.querySelector("#report-testSql").value.trim();
        if (testSql != "") {
            result["testSql"] = testSql;
        }

        let localAttach = document.querySelector("#report-local-attach");
        if (localAttach != null) {
            if (localAttach.value.trim() != "") {
                result["local_attach"] = localAttach.value.trim();
            }
        }

        document.querySelectorAll(".custom-info").forEach((e) => {
            let v = getVal(e);
            let k = e.name;
            if (v !== "") {
                result[k] = v;
            }
        });
        return result;
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

    // ajax 执行读取表列信息
    readCols() {
        let promise = new Promise(function (resolve, reject) {
            let k = $("#report-database").val() + $("#report-table").val();
            if (panel.cols.hasOwnProperty(k)) {
                resolve();
                return;
            }
            panel.progress = "表列信息读取中...";
            let db = encodeURIComponent($("#report-database").val());
            let table = encodeURIComponent($("#report-table").val());
            let url = ["/get-cols", db, table].join("/");
            let callbacks = {
                success: (xhr) => {
                    panel.cols = Object.assign(panel.cols, xhr);
                    panel.progress = "表列信息获取完毕.";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    renderCols() {
        let k = $("#report-database").val() + $("#report-table").val();
        let ul = $(".col-list");
        ul.children().remove();
        panel.cols[k].forEach(e => {
            let l = document.createElement("li");
            l.innerText = e;
            l.addEventListener("click", function () {
                let name = panel.activeCol;
                $("input[name='" + name + "']").val($(this).text());
            });
            ul.append(l);
        });
    }

    // ajax 执行创建动作
    createMail() {
        let promise = new Promise(function (resolve, reject) {
            if (!panel.checkReport()) {
                reject();
                return;
            }
            panel.progress = "创建请求发送中...";
            let url = "/create";
            let data = panel.currentReport;
            let callbacks = {
                success: (xhr) => {
                    let mail = panel.currentReport;
                    mail["id"] = xhr["id"];
                    mail["post_time"] = timeconverter(mail["post_time"]);
                    panel.mailList.push(mail);
                    panel.renderMailsTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    // ajax 执行读取邮件列表
    readMails() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "全部报表信息读取中...";
            let url = "/mail-list";
            let callbacks = {
                success: (xhr) => {
                    let mails = xhr.values.map(row => {
                        let r = {};
                        xhr.columns.forEach((k, i) => r[k] = row[i]);
                        r["post_time"] = timeconverter(r["post_time"]);
                        r["complete_time"] = timeconverter(r["complete_time"]);
                        r["info"] = typeof r["info"] == "string" ? JSON.parse(r["info"]) : r["info"];
                        return r;
                    });
                    panel.mailList = mails;
                    panel.renderMailsTable();
                    panel.progress = "全部报表信息获取完毕.";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 执行修改邮件信息
    updateMail() {
        if (panel.currentReportId == null) {
            return this.createMail();
        }

        let promise = new Promise(function (resolve, reject) {
            if (!panel.checkReport()) {
                reject();
                return;
            }

            let url = "/update";
            let data = panel.currentReport;
            let callbacks = {
                success: (xhr) => {
                    let i = panel.mailList.findIndex(e => e["id"] == data.id);
                    data["post_time"] = timeconverter(data["post_time"]);
                    data["complete_time"] = panel.mailList[i]["complete_time"];
                    panel.mailList[i] = data;
                    panel.renderMailsTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            panel.progress = "修改信息发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    // ajax 执行删除操作
    deleteMail() {
        let promise = new Promise(function (resolve, reject) {
            if (panel.currentReportId == null) {
                panel.progress = "当前无选中的报表.";
                reject();
                return;
            }

            let id = panel.currentReportId;
            let url = "/delete/" + id;
            let callbacks = {
                success: (xhr) => {
                    panel.mailList = panel.mailList.filter(e => e["id"] != id);
                    panel.currentReportId = "";
                    panel.renderMailsTable();
                    panel.progress = xhr["response"];
                }
            };
            panel.allowChange = false;
            panel.progress = "删除请求发送中...";
            getJSON(url, callbacks, resolve, reject, "POST");
        });
        return promise;
    }

    // ajax 尝试投递一封邮件
    tryPost() {
        let promise = new Promise(function (resolve, reject) {
            if ($("#test-mail").val().trim() === "") {
                panel.progress = "未填写测试邮箱";
                reject();
                return;
            }
            let url = "/try-post";
            let data = {
                name: panel.currentReport.name,
                receiver: $("#test-mail").val(),
                builder_name: panel.currentBuilder,
                info: panel.readInfo()
            };
            let callbacks = { success: (xhr) => { panel.progress = xhr["response"]; } };
            panel.progress = "测试邮件发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    // ajax 立即发送邮件
    postNow() {
        let promise = new Promise(function (resolve, reject) {
            let url = "/post-now";
            let data = panel.currentReport;
            let callbacks = {
                success: (xhr) => {
                    panel.progress = xhr["response"];
                    panel.mailList.find(e => e["id"] == data.id)["complete_time"] = timeconverter(xhr["time"]);
                    panel.renderMailsTable();
                }
            };
            panel.progress = "邮件发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    // ajax 获取一个报表的控件 info 模板
    getInfoTemplate() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "获取报表自定义信息列表中...";
            let url = "/get-info-template/" + panel.currentBuilder;
            let callbacks = {
                success: (xhr) => {
                    panel.currentInfoTemplate = xhr;
                    panel.progress = "报表自定义信息列表获取完成.";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // ajax 获取当前所有的生成器类, 测试 ok
    getBuilderList() {
        let promise = new Promise(function (resolve, reject) {
            panel.progress = "获取全部报表类型中...";
            let url = "/get-builder-list";
            let callbacks = {
                success: (xhr) => {
                    panel.builderList = xhr;
                    panel.progress = "全部报表类型获取完成.";
                }
            };
            getJSON(url, callbacks, resolve, reject, "GET");
        });
        return promise;
    }

    // 在新窗口打开邮件页面
    checkMailHtml() {
        let promise = new Promise(function (resolve, reject) {
            let url = "/check-html";
            let callbacks = {
                success: (xhr) => {
                    panel.progress = "报表已生成,请在新建的窗口中查看";
                    myWindow.document.write(xhr["html"]);
                    myWindow.focus();
                }
            };
            let data = panel.currentReport;
            let myWindow = window.open('', '', 'width=480,height=640');
            panel.progress = "请求发送中,完成后新窗口中会填充报表内容...";
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    // 在新窗口打开SQL进行确认
    checkSql() {
        let promise = new Promise(function (resolve, reject) {
            let url = "/check-sql";
            let callbacks = {
                success: (xhr) => {
                    panel.progress = "SQL已获取, 请在新建的窗口中查看";
                    myWindow.document.write("<pre>" + xhr["sql"] + "</pre>");
                    myWindow.focus();
                }
            };
            let data = panel.currentReport;
            let myWindow = window.open('', '', 'width=720,height=480');
            data["func"] = $("#sql-funcs").val();
            data["args"] = $("#sql-args").val().trim();
            panel.progress = "获取SQL请求发送中...";
            getJSON(url, callbacks, resolve, reject, "POST", data);
        });
        return promise;
    }

    showLoading() {
        $("#loading-symbol").css("opacity", "1");
    }

    hideLoading() {
        $("#loading-symbol").css("opacity", "0");
    }
}

var panel = new Panel();
panel.getBuilderList()
    .then(() => {
        panel.renderBuilderOptions();
        return panel.getInfoTemplate();
    })
    .then(() => panel.renderInfoInputs());
panel.readMails();
panel.readDbSet()
    .then(() => {
        panel.renderDatabaseOptions();
        panel.renderTableOptions();
        panel.readCols().then(() => { panel.renderCols(); });
    });

