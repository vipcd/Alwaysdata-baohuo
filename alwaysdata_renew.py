#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alwaysdata 自动续期脚本
- 通过模拟登录刷新免费账号活跃状态
- 支持 Telegram 通知（可选）
"""

import os
import sys
import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
# Telegram 通知（可选）
# ──────────────────────────────────────────────
def send_telegram(token: str, chat_id: str, text: str) -> None:
    """发送 Telegram 消息，失败时仅打印警告，不影响主流程。"""
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  Telegram 通知发送失败（不影响主流程）: {e}")


# ──────────────────────────────────────────────
# 核心登录逻辑
# ──────────────────────────────────────────────
def alwaysdata_renew(username: str, password: str) -> bool:
    if not username or not password:
        print("❌ 错误：未配置 ALWAYSDATA_USER 或 ALWAYSDATA_PASS 环境变量！")
        return False

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://admin.alwaysdata.com/login/",
        "Origin":  "https://admin.alwaysdata.com",
    })

    login_url = "https://admin.alwaysdata.com/login/"

    # ── Step 1: 获取登录页并提取 CSRF Token ──
    print("🔄 正在获取 Alwaysdata 登录页 Token...")
    try:
        resp = session.get(login_url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 无法访问登录页: {e}")
        return False

    soup = BeautifulSoup(resp.text, "html.parser")
    csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
    if not csrf_input:
        print("❌ 未能在页面中找到 csrfmiddlewaretoken，页面结构可能已变更。")
        return False

    csrf_token = csrf_input.get("value", "")
    print(f"🔑 成功提取 Token: {csrf_token[:8]}...")

    # ── Step 2: 发送登录 POST ──
    payload = {
        "csrfmiddlewaretoken": csrf_token,
        "login":    username,
        "password": password,
        "alive":    "on",
    }
    print("🚀 正在发送 POST 登录请求...")
    try:
        login_resp = session.post(login_url, data=payload, timeout=20)
        login_resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ 登录 POST 请求失败: {e}")
        return False

    # ── Step 3: 验证 sessionid ──
    if "sessionid" not in session.cookies.get_dict():
        print("❌ 登录失败：响应中未获取到 sessionid Cookie。")
        print(f"   HTTP 状态码: {login_resp.status_code}")
        print(f"   最终 URL:    {login_resp.url}")
        return False

    print("✅ sessionid 已获取，登录成功！")

    # ── Step 4: 访问 Dashboard 确认账号活跃 ──
    print("🔍 正在访问管理面板以确认账号活跃状态...")
    try:
        dashboard_resp = session.get(
            "https://admin.alwaysdata.com/", timeout=20
        )
        # 若被重定向回登录页，说明会话无效
        if "login" in dashboard_resp.url:
            print("❌ 会话无效：访问面板后被重定向回登录页。")
            return False
        print(f"✅ 面板访问成功（HTTP {dashboard_resp.status_code}），账号续期完成！")
    except requests.RequestException as e:
        # 能拿到 sessionid 就算基本成功，此处仅警告
        print(f"⚠️  访问面板时发生网络错误（不影响续期结果）: {e}")

    return True


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    ALWAYSDATA_USER = os.getenv("ALWAYSDATA_USER", "").strip()
    ALWAYSDATA_PASS = os.getenv("ALWAYSDATA_PASS", "").strip()
    TG_BOT_TOKEN    = os.getenv("TG_BOT_TOKEN", "").strip()
    TG_CHAT_ID      = os.getenv("TG_CHAT_ID", "").strip()

    success = alwaysdata_renew(ALWAYSDATA_USER, ALWAYSDATA_PASS)

    if success:
        send_telegram(
            TG_BOT_TOKEN, TG_CHAT_ID,
            "✅ <b>Alwaysdata 续期成功</b>\n账号登录及面板访问均正常，活跃状态已刷新。"
        )
    else:
        send_telegram(
            TG_BOT_TOKEN, TG_CHAT_ID,
            "❌ <b>Alwaysdata 续期失败</b>\n请检查 GitHub Actions 日志。"
        )
        sys.exit(1)
