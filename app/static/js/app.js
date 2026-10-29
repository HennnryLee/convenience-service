/* 便民服务平台 —— 前端交互脚本
   1) 提交表单时显示"加载中"提示，防止用户重复提交（用户交互的反馈机制）
   2) 提示条 5 秒后自动淡出
*/
(function () {
    "use strict";

    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form || form.dataset.noLoading === "true") { return; }
        var btn = form.querySelector("button[type=submit], input[type=submit]");
        if (!btn || btn.disabled) { return; }
        btn.disabled = true;

        var tip = document.createElement("span");
        tip.className = "loading active";
        tip.textContent = "提交中，请稍候…";
        btn.parentNode.appendChild(tip);

        // 兜底：8 秒后恢复按钮，避免异常情况下按钮长期不可用
        window.setTimeout(function () {
            btn.disabled = false;
            if (tip.parentNode) { tip.parentNode.removeChild(tip); }
        }, 8000);
    });

    document.addEventListener("DOMContentLoaded", function () {
        var alerts = document.querySelectorAll(".alert");
        window.setTimeout(function () {
            alerts.forEach(function (el) {
                el.style.transition = "opacity .6s";
                el.style.opacity = "0";
                window.setTimeout(function () {
                    if (el.parentNode) { el.parentNode.removeChild(el); }
                }, 600);
            });
        }, 5000);
    });
})();
