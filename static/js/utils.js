
// 获取 input 控件的值
function getVal(x) {
    if (x.type == "checkbox") {
        return x.checked;
    }
    let v = x.value;
    if (v.toUpperCase() == "TRUE") {
        return true;
    }
    if (v.toUpperCase() == "FALSE") {
        return false;
    }
    if (parseFloat(v) == v) {
        return parseFloat(v);
    }
    return v.toString().trim();
};

// 设置 input 控件的值
function setVal(x, val) {
    if (x.type == "checkbox") {
        if (val === "") {
            val = false;
        }
        x.checked = val;
        return;
    }
    x.value = val;
    if (x.type == "select-one") {
        if (val == "") {
            return;
        }
        if (x.value == "") {
            $(x).append("<option>" + val + "</option>");
            x.value = val;
        }
    }
}

// 把时间和秒数互相转化
function timeconverter(val) {
    if (val === null) {
        return "";
    }
    let format = (num) => num <= 9 ? "0" + num.toString() : num.toString();
    if (typeof val == "number") {
        if (val > 86400) {
            return "无需投递";
        }
        let h = Math.floor(val / 3600);
        let m = Math.floor((val - h * 3600) / 60);
        return [format(h), ":", format(m)].join("");
    } else {
        let hm = val.split(":");
        let h = parseInt(hm[0]);
        let m = parseInt(hm[1]);
        return h * 3600 + m * 60;
    }
}

// 设置特定 select 元素的选项
function setSelectOptions(target, vals) {
    // 为 select 元素设置一组选项        
    target = "#" + target;
    $(target).children().remove();
    let options = [];
    if (vals.hasOwnProperty("length")) {
        options = vals.map(e => {
            let o = document.createElement("option");
            o.innerText = e;
            return o;
        });
    } else {
        options = Object.keys(vals).map(e => {
            let o = document.createElement("option");
            o.innerText = e;
            o.setAttribute("value", vals[e]);
            return o;
        });
    }
    options.forEach(e => $(target).append(e));
}

//添加访问统计
function addAccessLog() {
    let data = {
        host: "mail",
        route: window.location.pathname
    };
    data = JSON.stringify(data);
    $.post("/add-access-log", data);
}


// ajax 交互方法封装
function getJSON(url, callbacks, resolve, reject, method, data) {
    let errorfunc = (func, xhr) => {
        if (func != undefined) {
            func(xhr);
        } else {
            panel.progress = xhr["error"];
            console.log(xhr["tb"]);
        }
    };

    let obj = {
        url: url,
        dataType: "JSON",
        success: (xhr) => {
            if (xhr["error"] != undefined) {
                errorfunc(callbacks["error"], xhr);
                reject();
                return;
            }
            callbacks["success"](xhr);
            resolve();
        },
        error: (xhr) => {
            xhr["error"] = ("连接或响应错误:\n" + xhr["status"] + "\n" + xhr["responseText"]);
            errorfunc(callbacks["error"], xhr);
            reject();
            return;
        },
        complete: () => {
            panel.allowChange = true;
            $("#loading-symbol").css("opacity", "0");
            if (callbacks["complete"] != undefined) {
                callbacks["complete"]();
            }
        }
    };

    if (method == "POST") {
        obj["type"] = "POST";
        obj["data"] = JSON.stringify(data);
    }

    $.ajax(obj);
    $("#loading-symbol").css("opacity", "1");
}

addAccessLog()