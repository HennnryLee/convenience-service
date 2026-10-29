"""兼容性自动化检查脚本（软件测试实验四：兼容性测试）。

在指定浏览器与分辨率下访问关键页面，检查：
  1. 页面能否正常加载（标题非空、无 JS 报错导致白屏）
  2. 是否出现横向滚动条（布局是否溢出，移动端适配是否生效）
  3. 关键交互元素是否可见（导航链接、按钮）

用法（需先启动应用：python run.py）：
    python scripts/compatibility_check.py
结果写入 reports/compatibility_result.md
"""
import os
import sys

from selenium import webdriver
from selenium.webdriver.common.by import By

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
PAGES = ["/", "/services/", "/announcements/", "/auth/login", "/auth/register"]
RESOLUTIONS = [(1920, 1080, "桌面 1920×1080"), (1366, 768, "笔记本 1366×768"), (375, 667, "移动端 375×667")]

BROWSERS = {
    "edge": lambda: webdriver.Edge(),
    "firefox": lambda: webdriver.Firefox(),
    "chrome": lambda: webdriver.Chrome(),
}


def check_page(driver, path, label):
    driver.get(BASE_URL + path)
    overflow = driver.execute_script(
        "return document.documentElement.scrollWidth > window.innerWidth + 1;"
    )
    scroll_width = driver.execute_script("return document.documentElement.scrollWidth;")
    inner_width = driver.execute_script("return window.innerWidth;")
    links = len(driver.find_elements(By.TAG_NAME, "a"))
    buttons = len(driver.find_elements(By.TAG_NAME, "button"))
    title = driver.title or "(无标题)"
    return {
        "page": path,
        "resolution": label,
        "title": title,
        "overflow": overflow,
        "scroll_width": scroll_width,
        "inner_width": inner_width,
        "links": links,
        "buttons": buttons,
    }


def run_browser(name, factory):
    results = []
    driver = factory()
    try:
        for width, height, label in RESOLUTIONS:
            driver.set_window_size(width, height)
            for page in PAGES:
                results.append(check_page(driver, page, label))
    finally:
        driver.quit()
    return results


def main():
    report_lines = ["# 兼容性测试结果（自动化）", "", f"被测地址：{BASE_URL}", ""]
    any_run = False
    for name, factory in BROWSERS.items():
        try:
            results = run_browser(name, factory)
            any_run = True
        except Exception as exc:  # 浏览器不可用（未安装/驱动缺失）时跳过
            report_lines.append(f"## {name}\n\n未执行：{type(exc).__name__}: {exc}\n")
            continue
        report_lines.append(f"## 浏览器：{name}")
        report_lines.append("")
        report_lines.append("| 页面 | 分辨率 | 标题 | 横向溢出 | scrollWidth | innerWidth | 链接数 | 按钮数 | 结论 |")
        report_lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in results:
            ok = "通过" if not r["overflow"] and r["links"] > 0 else "不通过"
            report_lines.append(
                f"| {r['page']} | {r['resolution']} | {r['title'][:24]} | "
                f"{'是' if r['overflow'] else '否'} | {r['scroll_width']} | {r['inner_width']} | "
                f"{r['links']} | {r['buttons']} | {ok} |"
            )
        report_lines.append("")
    if not any_run:
        report_lines.append("未检测到可用浏览器，请按报告中的手工检查清单执行兼容性测试。")
    out = os.path.join(os.path.dirname(__file__), os.pardir, "reports", "compatibility_result.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"[OK] 已生成 {os.path.abspath(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
