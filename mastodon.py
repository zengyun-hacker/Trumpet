#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mastodon Alfred Workflow
支持配置域名、OAuth 登录和发送嘟文
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import webbrowser

# Alfred Workflow Data 目录
BUNDLE_ID = "com.alfred.mastodon"
DATA_DIR = os.path.expanduser(f"~/Library/Application Support/Alfred/Workflow Data/{BUNDLE_ID}")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# OAuth 配置
APP_NAME = "Alfred Mastodon"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
SCOPES = "read write"


def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置"""
    ensure_data_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def api_request(instance, endpoint, method="GET", data=None, token=None):
    """发送 API 请求"""
    url = f"https://{instance}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AlfredMastodon/1.0"
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if data:
        data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"API 错误 {e.code}: {error_body}")


def alfred_output(items):
    """输出 Alfred JSON 格式"""
    print(json.dumps({"items": items}, ensure_ascii=False))


def cmd_config(domain):
    """配置 Mastodon 实例域名"""
    domain = domain.strip().lower()
    if not domain:
        alfred_output([{
            "title": "请输入 Mastodon 实例域名",
            "subtitle": "例如: mastodon.social",
            "valid": False
        }])
        return

    # 移除协议前缀
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.rstrip("/")

    alfred_output([{
        "title": f"配置实例: {domain}",
        "subtitle": "按回车确认",
        "arg": domain,
        "valid": True
    }])


def cmd_config_save(domain):
    """保存域名配置"""
    config = load_config()
    config["instance"] = domain
    # 清除旧的认证信息
    config.pop("client_id", None)
    config.pop("client_secret", None)
    config.pop("access_token", None)
    save_config(config)
    print(f"已配置实例: {domain}")


def cmd_login():
    """开始 OAuth 登录流程"""
    config = load_config()
    instance = config.get("instance")

    if not instance:
        alfred_output([{
            "title": "请先配置 Mastodon 实例",
            "subtitle": "运行 mast config <domain>",
            "valid": False
        }])
        return

    alfred_output([{
        "title": f"登录到 {instance}",
        "subtitle": "按回车打开浏览器进行授权",
        "arg": "login",
        "valid": True
    }])


def cmd_login_execute():
    """执行登录：注册应用并打开授权页面"""
    config = load_config()
    instance = config.get("instance")

    if not instance:
        print("错误: 请先配置实例")
        return

    # 注册应用
    try:
        app_data = api_request(instance, "/api/v1/apps", method="POST", data={
            "client_name": APP_NAME,
            "redirect_uris": REDIRECT_URI,
            "scopes": SCOPES,
            "website": "https://github.com/user/alfred-mastodon"
        })

        config["client_id"] = app_data["client_id"]
        config["client_secret"] = app_data["client_secret"]
        save_config(config)

        # 构建授权 URL
        auth_params = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": app_data["client_id"],
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES
        })
        auth_url = f"https://{instance}/oauth/authorize?{auth_params}"

        # 打开浏览器
        webbrowser.open(auth_url)
        print("已打开浏览器，请授权后复制授权码，运行 mast auth <code>")

    except Exception as e:
        print(f"登录失败: {e}")


def cmd_auth(code):
    """输入授权码"""
    code = code.strip()
    if not code:
        alfred_output([{
            "title": "请输入授权码",
            "subtitle": "从浏览器复制授权码",
            "valid": False
        }])
        return

    alfred_output([{
        "title": f"使用授权码登录",
        "subtitle": "按回车确认",
        "arg": code,
        "valid": True
    }])


def cmd_auth_execute(code):
    """使用授权码获取 access token"""
    config = load_config()
    instance = config.get("instance")
    client_id = config.get("client_id")
    client_secret = config.get("client_secret")

    if not all([instance, client_id, client_secret]):
        print("错误: 请先运行 mast login")
        return

    try:
        # 获取 access token
        token_data = api_request(instance, "/oauth/token", method="POST", data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI
        })

        config["access_token"] = token_data["access_token"]
        save_config(config)

        # 验证并获取用户信息
        user = api_request(instance, "/api/v1/accounts/verify_credentials", token=token_data["access_token"])
        print(f"登录成功! 欢迎 @{user['username']}@{instance}")

    except Exception as e:
        print(f"授权失败: {e}")


def cmd_toot(text):
    """准备发送嘟文"""
    config = load_config()

    if not config.get("access_token"):
        alfred_output([{
            "title": "请先登录",
            "subtitle": "运行 mast login",
            "valid": False
        }])
        return

    text = text.strip()
    if not text:
        alfred_output([{
            "title": "输入要发送的嘟文",
            "subtitle": "支持最多 500 字符",
            "valid": False
        }])
        return

    char_count = len(text)
    alfred_output([{
        "title": text[:50] + ("..." if len(text) > 50 else ""),
        "subtitle": f"按回车发送 ({char_count} 字符)",
        "arg": text,
        "valid": True
    }])


def cmd_toot_send(text):
    """发送嘟文"""
    config = load_config()
    instance = config.get("instance")
    token = config.get("access_token")

    if not all([instance, token]):
        print("错误: 请先登录")
        return

    try:
        result = api_request(instance, "/api/v1/statuses", method="POST",
                            data={"status": text}, token=token)
        print(f"发送成功! {result.get('url', '')}")
    except Exception as e:
        print(f"发送失败: {e}")


def main():
    if len(sys.argv) < 2:
        print("用法: mastodon.py <command> [args]")
        return

    command = sys.argv[1]
    args = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    commands = {
        "config": lambda: cmd_config(args),
        "config_save": lambda: cmd_config_save(args),
        "login": cmd_login,
        "login_execute": cmd_login_execute,
        "auth": lambda: cmd_auth(args),
        "auth_execute": lambda: cmd_auth_execute(args),
        "toot": lambda: cmd_toot(args),
        "toot_send": lambda: cmd_toot_send(args),
    }

    if command in commands:
        commands[command]()
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    main()
