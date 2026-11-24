"""把部署模板渲染为可直接使用的配置（避免手改域名/证书路径/项目路径）。

用法：
    DEPLOY_DOMAIN=example.com \
    DEPLOY_CERT_DIR=/etc/letsencrypt/live/example.com \
    DEPLOY_APP_DIR=/srv/convenience_service \
    DEPLOY_SERVICE_USER=www-data \
    DEPLOY_ENV_FILE=/etc/convenience.env \
    python deploy/render_configs.py

输出：
    deploy/generated/nginx.conf
    deploy/generated/convenience.service

设计说明：
    - 用 ``{{NAME}}`` 占位而不是 shell ``$NAME``，避免与 Nginx 的 $host/$request_id 变量冲突；
    - 未设置的环境变量回退到示例值，便于本地预览；生产渲染后应人工 review；
    - 生成目录已加入 .gitignore，避免把真实域名/证书路径提交进仓库。
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "generated"

VALUES = {
    "DOMAIN": os.environ.get("DEPLOY_DOMAIN", "example.com"),
    "CERT_DIR": os.environ.get("DEPLOY_CERT_DIR", "/etc/letsencrypt/live/example.com"),
    "APP_DIR": os.environ.get("DEPLOY_APP_DIR", "/srv/convenience_service"),
    "SERVICE_USER": os.environ.get("DEPLOY_SERVICE_USER", "www-data"),
    "ENV_FILE": os.environ.get("DEPLOY_ENV_FILE", "/etc/convenience.env"),
    "UPSTREAM": os.environ.get("DEPLOY_UPSTREAM", "127.0.0.1:8000"),
}

TEMPLATES = {
    "nginx.conf": "nginx.conf.template",
    "convenience.service": "convenience.service.template",
}


def render(template_text: str, values: dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def render_all(output_dir: Path = DEFAULT_OUTPUT) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for output_name, template_name in TEMPLATES.items():
        template_text = (ROOT / template_name).read_text(encoding="utf-8")
        target = output_dir / output_name
        target.write_text(render(template_text, VALUES), encoding="utf-8")
        written.append(target)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="渲染 Nginx/systemd 部署配置")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        help="输出目录（默认 deploy/generated）",
    )
    args = parser.parse_args(argv)
    written = render_all(Path(args.output_dir))
    print("[OK] 已渲染：")
    for path in written:
        print(f"  -> {path}")
    print("请按实际域名/证书/项目路径 review 后再复制到 /etc/nginx 与 /etc/systemd/system。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
