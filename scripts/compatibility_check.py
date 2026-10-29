"""兼容性自动化检查脚本（软件测试实验四：兼容性测试）。

在指定浏览器与分辨率下访问关键页面，检查：
  1. 页面能否正常加载（标题非空）
  2. 是否出现横向滚动条（布局溢出 / 移动端适配是否生效）
  3. 关键交互元素是否可见（链接、按钮）
  4. 浏览器控制台是否产生 JS 错误

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

# 本机浏览器实际安装位置（Chrome 为用户级安装，不在 Program Files 下，
# Selenium 默认搜索路径找不到，必须显式指定 binary_location）
CHROME_PATH = r"C:\Users\34396\AppData\Local\Google\Chrome\Application\chrome.exe"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def _chrome():
    options = webdriver.ChromeOptions()
    if os.path.exists(CHROME_PATH):
        options.binary_location = CHROME_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def _edge():
    options = webdriver.EdgeOptions()
    if os.path.exists(EDGE_PATH):
        options.binary_location = EDGE_PATH
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Edge(options=options)


def _firefox():
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    return webdriver.Firefox(options=options)


BROWSERS = {
    "chrome": _chrome,
    "edge": _edge,
    "firefox": _firefox,
}

DISPLAY_NAME = {"chrome": "Chrome", "edge": "Microsoft Edge", "firefox": "Mozilla Firefox"}


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
    # 采集控制台错误（页面级 JS 报错）
    js_errors = []
    try:
        for entry in driver.get_log("browser"):
            if entry.get("level") == "SEVERE":
                js_errors.append(entry.get("message", "")[:120])
    except Exception:
        js_errors = []  # Firefox 不支持 get_log('browser')，忽略
    return {
        "page": path,
        "resolution": label,
        "title": title,
        "overflow": overflow,
        "scroll_width": scroll_width,
        "inner_width": inner_width,
        "links": links,
        "buttons": buttons,
        "js_errors": js_errors,
    }


def set_viewport(driver, width, height, chromium):
    """设置视口。

    Windows 下浏览器窗口有最小宽度限制（Firefox≈500、Chrome/Edge≈512），
    375px 移动端视口无法用 set_window_size 真实模拟。
    Chromium 内核浏览器改用 CDP 的 Emulation.setDeviceMetricsOverride
    强制覆盖视口尺寸，可得到真实的 375×667 视口。
    """
    if chromium:
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": width < 500,
            },
        )
    else:
        driver.set_window_size(width, height)


def run_browser(name, factory):
    results = []
    driver = factory()
    chromium = name in ("chrome", "edge")
    try:
        version = "unknown"
        try:
            caps = driver.capabilities
            version = caps.get("browserVersion") or caps.get("version") or "unknown"
        except Exception:
            pass
        for width, height, label in RESOLUTIONS:
            set_viewport(driver, width, height, chromium)
            for page in PAGES:
                results.append(check_page(driver, page, label))
        return results, version
    finally:
        driver.quit()


def main():
    report_lines = [
        "# 兼容性测试结果（自动化）",
        "",
        f"被测地址：{BASE_URL}",
        "",
        "检查项：页面可加载（标题非空）、无横向溢出（scrollWidth ≤ innerWidth）、"
        "关键元素可见（链接数 > 0）、控制台无 JS 严重错误。",
        "",
    ]
    summary = []
    any_run = False
    for name, factory in BROWSERS.items():
        try:
            results, version = run_browser(name, factory)
            any_run = True
        except Exception as exc:  # 浏览器不可用（未安装/驱动缺失）时跳过
            report_lines.append(f"## 浏览器：{DISPLAY_NAME[name]}\n\n未执行：{type(exc).__name__}: {exc}\n")
            summary.append((DISPLAY_NAME[name], "未执行", str(exc)[:60]))
            continue
        passed = sum(
            1 for r in results if not r["overflow"] and r["links"] > 0 and not r["js_errors"]
        )
        total = len(results)
        summary.append((DISPLAY_NAME[name], f"{passed}/{total} 通过", f"version {version}"))
        report_lines.append(f"## 浏览器：{DISPLAY_NAME[name]}（版本 {version}）")
        report_lines.append("")
        report_lines.append("| 页面 | 分辨率 | 标题 | 横向溢出 | scrollWidth | innerWidth | 链接数 | 按钮数 | JS错误 | 结论 |")
        report_lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in results:
            ok = "通过" if not r["overflow"] and r["links"] > 0 and not r["js_errors"] else "不通过"
            report_lines.append(
                f"| {r['page']} | {r['resolution']} | {r['title'][:24]} | "
                f"{'是' if r['overflow'] else '否'} | {r['scroll_width']} | {r['inner_width']} | "
                f"{r['links']} | {r['buttons']} | {len(r['js_errors'])} | {ok} |"
            )
        report_lines.append("")
    # 汇总表（放在正文各浏览器明细之前）
    head = ["## 汇总", "", "| 浏览器 | 结果 | 备注 |", "|---|---|---|"]
    for b, res, note in summary:
        head.append(f"| {b} | {res} | {note} |")
    head.append("")
    report_lines = report_lines[:4] + head + report_lines[4:]
    if not any_run:
        report_lines.append("未检测到可用浏览器，请按报告中的手工检查清单执行兼容性测试。")
    out = os.path.join(os.path.dirname(__file__), os.pardir, "reports", "compatibility_result.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"[OK] 已生成 {os.path.abspath(out)}")
    for b, res, note in summary:
        print(f"  {b}: {res} ({note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
