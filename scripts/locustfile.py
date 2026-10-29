"""Locust 性能测试脚本（软件测试实验四：性能测试）。

场景：浏览首页、服务查询（含关键词）、服务详情、公告列表、登录后查看我的预约、提交预约。
令牌处理：开发环境启用了 CSRF 防护，脚本会先从页面提取 csrf_token 再提交表单。

运行：
    locust -f scripts/locustfile.py --headless -u 50 -r 10 -t 30s \
           --host http://127.0.0.1:5000 --csv=reports/perf_50
"""
import random
import re
from datetime import date, timedelta

from locust import HttpUser, between, task

BOOKING_DATE = (date.today() + timedelta(days=random.choice([3, 5, 7]))).isoformat()

CSRF_PATTERN = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


def extract_csrf(html):
    match = CSRF_PATTERN.search(html)
    return match.group(1) if match else ""


class ConvenienceUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """每个虚拟用户启动后先登录（模拟真实用户会话）。"""
        html = self.client.get("/auth/login").text
        token = extract_csrf(html)
        self.client.post(
            "/auth/login",
            data={"csrf_token": token, "login": "zhangsan", "password": "User@123"},
            name="POST /auth/login",
        )

    @task(3)
    def index(self):
        self.client.get("/", name="GET /")

    @task(3)
    def search_services(self):
        keyword = random.choice(["身份证", "维修", "体检", "", "社保"])
        self.client.get(f"/services/?keyword={keyword}", name="GET /services/?keyword")

    @task(2)
    def service_detail(self):
        self.client.get(f"/services/{random.randint(1, 12)}", name="GET /services/<id>")

    @task(1)
    def announcements(self):
        self.client.get("/announcements/", name="GET /announcements/")

    @task(1)
    def my_appointments(self):
        self.client.get("/appointments/mine", name="GET /appointments/mine")

    @task(1)
    def submit_appointment(self):
        service_id = random.randint(1, 12)
        # 预约表单页才包含 csrf_token，需先从该页面取令牌
        html = self.client.get(f"/appointments/create/{service_id}").text
        token = extract_csrf(html)
        self.client.post(
            f"/appointments/create/{service_id}",
            data={
                "csrf_token": token,
                "appointment_date": BOOKING_DATE,
                "time_slot": random.choice(["09:00-10:00", "10:00-11:00", "14:00-15:00"]),
                "contact_name": "压测用户",
                "contact_phone": "13800138000",
                "remark": "性能测试",
            },
            name="POST /appointments/create",
        )
