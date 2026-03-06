"""
从 TickTick API 获取专注数据和完成任务
默认取昨天，支持指定某一天: python ticktick_focus.py [YYYY-MM-DD]
可选 --diary 填入日记、--dingtalk 保存到钉钉工作日志

环境变量:
  TickTick: PYTICKTICK_V2_USERNAME, PYTICKTICK_V2_PASSWORD
  钉钉: DINGTALK_APP_KEY, DINGTALK_APP_SECRET, DINGTALK_USER_ID, DINGTALK_CORP_ID
      (CorpId 在管理后台-开发管理-开发信息 查看；配置后输出可点击链接)
      可选 DINGTALK_TEMPLATE_NAME(默认"日报"), DINGTALK_DD_FROM(默认"ticktick")
"""
import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 修复 pyticktick 与 TickTick/滴答清单 API 的兼容性
import pyticktick.settings
from pydantic import ValidationError

def _patched_v2_signon(cls, username, password, totp_secret, base_url, headers):
    resp = cls._v2_signon(username=username, password=password, base_url=base_url, headers=headers)
    try:
        totp_resp = __import__("pyticktick.models.v2.responses.user", fromlist=["UserSignOnWithTOTPV2"]).UserSignOnWithTOTPV2.model_validate(resp)
        if totp_secret is None:
            raise ValueError("Sign on requires TOTP verification")
        resp = cls._v2_mfa_verify(totp_secret, totp_resp.auth_id, base_url, headers)
    except (ValidationError, ValueError):
        pass
    if "userCode" in resp and isinstance(resp["userCode"], str) and len(resp["userCode"]) == 32:
        u = resp["userCode"]
        if u[12] in ("1", "2"):
            resp["userCode"] = u[:12] + "4" + u[13:]
    for k in ("registerDate",):
        resp.pop(k, None)
    from pyticktick.models.v2.responses.user import UserSignOnV2
    return UserSignOnV2.model_validate(resp)

pyticktick.settings.Settings.v2_signon = classmethod(_patched_v2_signon)

# 从 .env 加载
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def _day_range(dt: datetime):
    """某日 0 点和 24 点的毫秒时间戳（本地时区）"""
    start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

def _parse_date(s: str) -> datetime:
    """解析 YYYY-MM-DD 或 YYYYMMDD，返回当日 0 点（本地时区）"""
    s = s.strip().replace("-", "")
    return datetime.strptime(s[:8], "%Y%m%d").replace(hour=0, minute=0, second=0, microsecond=0)

def _push_dingtalk(target: datetime, content_text: str) -> str | None:
    """保存工作日志内容到钉钉，返回可打开的链接（无链接时返回 None）"""
    app_key = os.environ.get("DINGTALK_APP_KEY") or os.environ.get("DINGTALK_APPID")
    app_secret = os.environ.get("DINGTALK_APP_SECRET")
    user_id = os.environ.get("DINGTALK_USER_ID")
    corp_id = os.environ.get("DINGTALK_CORP_ID")
    template_name = os.environ.get("DINGTALK_TEMPLATE_NAME", "日报")
    dd_from = os.environ.get("DINGTALK_DD_FROM", "ticktick")
    if not all((app_key, app_secret, user_id)):
        print("钉钉需配置: DINGTALK_APP_KEY, DINGTALK_APP_SECRET, DINGTALK_USER_ID")
        return None
    try:
        import urllib.request
        import json
        base = "https://oapi.dingtalk.com"
        # 1. 获取 access_token
        req = urllib.request.urlopen(
            f"{base}/gettoken?appkey={app_key}&appsecret={app_secret}", timeout=10
        )
        tok = json.loads(req.read().decode())
        if tok.get("errcode") != 0:
            print(f"钉钉获取 token 失败: {tok}")
            return None
        token = tok["access_token"]
        # 2. 获取模板详情（含字段 sort/type/key）
        data = json.dumps({"userid": user_id, "template_name": template_name}).encode()
        req = urllib.request.Request(
            f"{base}/topapi/report/template/getbyname?access_token={token}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        tpl = json.loads(resp.read().decode())
        if tpl.get("errcode") != 0:
            print(f"钉钉获取模板失败: {tpl.get('errmsg', tpl)}")
            return None
        result = tpl.get("result") or {}
        template_id = result.get("id")
        fields = result.get("fields") or []
        # 取第一个文本类型字段 (type=1)
        text_field = next((f for f in fields if f.get("type") == 1), None)
        if not text_field:
            text_field = fields[0] if fields else {}
        sort_val = text_field.get("sort", 0)
        type_val = text_field.get("type", 1)
        key_val = text_field.get("field_name", "今日完成")
        if not template_id:
            print("钉钉模板未返回 id")
            return None
        # 3. 保存日志内容
        header = f"## {target.strftime('%Y-%m-%d')} 工作日志\n\n"
        body = {"create_report_param": {
            "template_id": template_id,
            "userid": user_id,
            "dd_from": dd_from,
            "contents": [{
                "sort": str(sort_val),
                "type": str(type_val),
                "content_type": "markdown",
                "content": header + content_text,
                "key": key_val,
            }],
        }}
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{base}/topapi/report/savecontent?access_token={token}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        out = json.loads(resp.read().decode())
        if out.get("errcode") == 0:
            content_id = out.get("result", "")
            if corp_id and content_id:
                from urllib.parse import quote
                redirect = f"https://landray.dingtalkapps.com/alid/app/reportpc/createreport.html?corpid={corp_id}&templateid={template_id}&contentid={content_id}&dd_from=ThirdParty"
                dingtalk_url = f"dingtalk://dingtalkclient/action/openapp?corpid={corp_id}&container_type=work_platform&app_id=2&redirect_type=jump&redirect_url={quote(redirect)}"
                print("已保存到钉钉，点击下方链接打开预填的写日志页面：")
                print(dingtalk_url)
                return dingtalk_url
            else:
                if not corp_id:
                    print("已保存。请配置 DINGTALK_CORP_ID 后可输出可点击的链接（管理后台-开发管理-开发信息 查看 CorpId）")
                else:
                    print("已保存到钉钉工作日志")
        else:
            print(f"钉钉保存失败: {out.get('errmsg', out)}")
        return None
    except Exception as e:
        print(f"钉钉推送错误: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(description="获取 TickTick 专注记录与完成任务")
    parser.add_argument("date", nargs="?", help="日期 YYYY-MM-DD，默认昨天")
    parser.add_argument("--diary", "-d", action="store_true", help="填入日记模板，写入 日记/YYYY-MM-DD.md")
    parser.add_argument("--dingtalk", action="store_true", help="保存到钉钉工作日志（需配置 DINGTALK_APP_KEY/SECRET/USER_ID）")
    args = parser.parse_args()

    if args.date:
        try:
            target = _parse_date(args.date)
        except ValueError:
            print(f"日期格式错误，请使用 YYYY-MM-DD: {args.date}")
            return
    else:
        target = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    target_start, target_end = _day_range(target)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    is_today = target.date() == today.date()
    label = "今日" if is_today else target.strftime("%Y-%m-%d")

    try:
        from pyticktick import Client
    except ImportError:
        print("请先安装: pip install pyticktick")
        return

    username = os.environ.get("PYTICKTICK_V2_USERNAME") or os.environ.get("TICKTICK_USERNAME")
    password = os.environ.get("PYTICKTICK_V2_PASSWORD") or os.environ.get("TICKTICK_PASSWORD")

    if not username or not password:
        print("需要配置 TickTick 账号:")
        print("  方式1: 环境变量 PYTICKTICK_V2_USERNAME, PYTICKTICK_V2_PASSWORD")
        print("  方式2: 同目录 .env 文件")
        print("\n滴答清单需设置 v2_base_url 为 https://api.dida365.com/api/v2/")
        return

    try:
        client = Client(
            v2_username=username,
            v2_password=password,
            override_forbid_extra=True,
        )

        lines: list[str] = []

        def out(s: str = ""):
            lines.append(s)

        # === 专注记录（pomodoros 接口）===
        out(f"## 专注记录（{label}）")

        def _fmt_time(iso_str: str) -> str:
            """将 ISO 时间转为本地 'H:MM 上午/下午/晚上'"""
            if not iso_str:
                return ""
            try:
                s = str(iso_str).replace("+0000", "+00:00").replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                if dt.tzinfo:
                    dt = dt.astimezone()
                h = dt.hour
                if h < 12:
                    part = "上午"
                elif h < 18:
                    part = "下午"
                else:
                    part = "晚上"
                return f"{h}:{dt.minute:02d} {part}"
            except (ValueError, TypeError):
                return str(iso_str)

        total_min = 0
        record_count = 0
        task_count = 0
        merged_focus_lines: list[str] = []
        merged_tasks_lines: list[str] = []
        try:
            r = client._get_api_v2("pomodoros", {"from": target_start, "to": target_end})
            records = r if isinstance(r, list) else r.get("pomos", r.get("list", [])) or []
            if records:
                by_task: dict[str, int] = {}
                items: list[tuple[str, str, int, str]] = []  # (time_range, title_with_note, minutes, end_iso)
                for rec in records:
                    if not isinstance(rec, dict):
                        continue
                    dur = rec.get("length") or rec.get("duration") or rec.get("lengthMinutes") or 0
                    try:
                        d = int(dur) if isinstance(dur, (int, float)) else 0
                        if d > 1440:
                            d = d // 60000  # 毫秒转分钟
                        total_min += d
                    except (ValueError, TypeError):
                        d = 0
                    # 标题：优先 tasks[0].title（滴答清单实际结构）
                    tasks = rec.get("tasks") or []
                    task = tasks[0] if tasks and isinstance(tasks[0], dict) else {}
                    title = (
                        (task.get("title") or task.get("content")) if task
                        else rec.get("taskTitle") or rec.get("title") or rec.get("content")
                        or (rec.get("task") or {}).get("title") if isinstance(rec.get("task"), dict) else None
                    ) or "未知任务"
                    note = rec.get("note") or (task.get("note") if task else None)
                    if note and str(note).strip():
                        title_display = f"{title}（{note.strip()}）"
                    else:
                        title_display = title
                    by_task[title] = by_task.get(title, 0) + d
                    start_s = rec.get("startTime") or rec.get("startDate") or ""
                    end_s = rec.get("endTime") or rec.get("endDate") or ""
                    time_range = f"{_fmt_time(start_s)} - {_fmt_time(end_s)}" if (start_s and end_s) else ""
                    items.append((time_range, title_display, d, str(end_s)))
                record_count = len(records)
                out(f"{record_count} 条, 共 {total_min} 分钟")
                # 同任务合并：按任务名分组，汇总时长，收集想法
                merged: dict[str, dict] = {}  # title -> {total_min, notes: set, time_ranges: list}
                items.sort(key=lambda x: x[3], reverse=True)
                for time_range, title_display, m, _ in items:
                    base = title_display.split("（")[0].strip().rstrip()
                    if base not in merged:
                        merged[base] = {"total": 0, "notes": set(), "time_ranges": []}
                    merged[base]["total"] += m
                    merged[base]["time_ranges"].append(time_range)
                    if "（" in title_display:
                        note = title_display.split("（", 1)[1].rstrip("）").strip()
                        if note:
                            merged[base]["notes"].add(note)
                for base in sorted(merged.keys(), key=lambda k: -merged[k]["total"]):
                    info = merged[base]
                    suff = ""
                    if info["notes"]:
                        suff = f"（{'、'.join(info['notes'])}）"
                    line = f"- {base}{suff} {info['total']}m"
                    out(line)
                    merged_focus_lines.append(line)
            else:
                out("无记录")
        except Exception as e:
            out(f"获取失败 - {e}")

        # === 完成的任务 ===
        out("")
        out(f"## {label} 完成的任务")
        try:
            from pyticktick.models.v2.responses.closed import ClosedRespV2
            from pyticktick.pydantic import update_model_config

            day_begin = target.replace(hour=0, minute=0, second=0, microsecond=0)
            day_finish = day_begin + timedelta(days=1)
            closed_params = {
                "from": day_begin.strftime("%Y-%m-%d %H:%M:%S"),
                "to": day_finish.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Completed",
            }
            resp = client._get_api_v2("/project/all/closed", data=closed_params)
            if client.override_forbid_extra:
                update_model_config(ClosedRespV2, extra="allow")
            closed = ClosedRespV2.model_validate(resp)
            tasks = list(closed.root) if hasattr(closed, "root") else (closed if isinstance(closed, list) else [])
            task_count = len(tasks)
            if tasks:
                from collections import Counter
                titles = [
                    (getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else "?"))
                    for t in tasks
                ]
                counts = Counter(t.strip() or "?" for t in titles)
                for title, n in counts.most_common():
                    line = f"- {title}" + (f" x{n}" if n > 1 else "")
                    out(line)
                    merged_tasks_lines.append(f"- [x] {title}" + (f" x{n}" if n > 1 else ""))
                out(f"共 {len(tasks)} 项")
            else:
                out("无")
        except Exception as e:
            out(f"获取失败: {e}")

        # === 统计汇总（基于当日 pomodoros 本地时区）===
        out("")
        out("## 专注统计汇总")
        out(f"{label}: {record_count} 番茄, {total_min} 分钟")

        # 写入日记目录，文件名后缀为日期
        diary_dir = Path(__file__).parent
        out_path = diary_dir / f"ticktick_{target.strftime('%Y-%m-%d')}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"已写入: {out_path}")

        # 填入日记模板
        if args.diary:
            vault_root = diary_dir.parent
            template_path = vault_root / "模板" / "日记模板_每日笔记用.md"
            diary_path = diary_dir / f"{target.strftime('%Y-%m-%d')}.md"
            prev_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            next_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")
            if template_path.exists():
                tpl = template_path.read_text(encoding="utf-8")
                tpl = tpl.replace("{{date:YYYY-MM-DD}}", target.strftime("%Y-%m-%d"))
                tpl = tpl.replace("{{time:HH:mm}}", datetime.now().strftime("%H:%M"))
                tpl = tpl.replace("（创建后请手动补充日期链接，如 [[YYYY-MM-DD]]）", f"[[{prev_date}]]")
                tpl = tpl.replace("（创建后请手动补充日期链接）", f"[[{next_date}]]")
                # 填充 一句话总结：专注番茄数、时长、完成任务数
                parts = []
                if record_count > 0 or total_min > 0:
                    parts.append(f"专注 {record_count} 个番茄共 {total_min} 分钟")
                if task_count > 0:
                    parts.append(f"完成 {task_count} 项任务")
                summary = "；".join(parts) + "。" if parts else "（待补充）"
                tpl = tpl.replace("**一句话总结**：今天...", f"**一句话总结**：今天{summary}")
                today_done = merged_focus_lines if merged_focus_lines else merged_tasks_lines
                if not today_done:
                    today_done = ["- （待补充）"]
                done_block = "\n".join(today_done)
                import re
                tpl = re.sub(
                    r"(### 今日完成\n)((?:- .+\n?)+)",
                    lambda m: m.group(1) + done_block + "\n",
                    tpl,
                    count=1,
                )
                diary_path.write_text(tpl, encoding="utf-8")
                print(f"已填入日记: {diary_path}")
            else:
                print(f"未找到模板: {template_path}")

        # 钉钉工作日志
        diary_path = diary_dir / f"{target.strftime('%Y-%m-%d')}.md"
        dingtalk_url: str | None = None
        if args.dingtalk:
            today_done = merged_focus_lines if merged_focus_lines else merged_tasks_lines
            content_text = "\n".join(today_done) if today_done else "（无）"
            dingtalk_url = _push_dingtalk(target, content_text)
        if dingtalk_url:
            block = (
                f"\n\n## 钉钉工作日志\n\n"
                f"复制下方链接到**浏览器地址栏**或钉钉内打开（Cursor 内直接点会报错）：\n\n"
                f"```\n{dingtalk_url}\n```\n"
            )
            if diary_path.exists():
                diary_path.write_text(diary_path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
            else:
                diary_path.write_text(f"# {target.strftime('%Y-%m-%d')}\n{block}", encoding="utf-8")
            print(f"已写入链接到: {diary_path}")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
