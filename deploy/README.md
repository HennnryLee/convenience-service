# 生产部署示例（模板 + 渲染脚本）

## 为什么用模板

`nginx.conf.template` / `convenience.service.template` 里的域名、证书路径、项目目录因环境而异，
直接提交真实值容易泄露路径，手改又容易漏掉一处。现在改为：

```bash
DEPLOY_DOMAIN=your-domain.example \
DEPLOY_CERT_DIR=/etc/letsencrypt/live/your-domain.example \
DEPLOY_APP_DIR=/srv/convenience_service \
DEPLOY_SERVICE_USER=www-data \
DEPLOY_ENV_FILE=/etc/convenience.env \
python deploy/render_configs.py
```

生成：

- `deploy/generated/nginx.conf`
- `deploy/generated/convenience.service`

`deploy/generated/` 已在 `.gitignore` 中排除。渲染后请人工 review，再：

```bash
sudo cp deploy/generated/nginx.conf /etc/nginx/conf.d/convenience.conf
sudo nginx -t && sudo systemctl reload nginx
sudo cp deploy/generated/convenience.service /etc/systemd/system/convenience.service
sudo systemctl daemon-reload && sudo systemctl enable --now convenience
```

## Gunicorn

`deploy/gunicorn.conf.py` 通过环境变量配置：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `GUNICORN_BIND` | `127.0.0.1:8000` | 由 Nginx 反代时只监听本机 |
| `WEB_WORKERS` | CPU×2+1（上限 8） | worker 数 |
| `WEB_THREADS` | `2` | gthread 线程数 |
| `WEB_TIMEOUT` | `60` | 请求超时秒数 |
| `LOG_LEVEL` | `info` | gunicorn 日志级别 |

## 环境变量

生产至少需要：

```bash
FLASK_CONFIG=production
SECRET_KEY=<32 字节随机值>
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/convenience?charset=utf8mb4
LOG_LEVEL=INFO
```

完整发布/回滚步骤见 `docs/16-生产部署与数据库迁移.md`。
