# ticktick2md2ding

TickTick 专注记录与完成任务 → Obsidian 日记 + 钉钉工作日志。滴答清单数据自动写入 Markdown 并预填钉钉日报。

## 功能

- 从滴答清单拉取**专注记录**（含时间、任务名、时长、想法）和**完成任务**
- 同任务合并，输出精简的 Markdown
- 可填入 Obsidian 日记模板
- 可推送至钉钉工作日志，生成预填链接
- 支持开机自动运行（Windows 计划任务）

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env`，填写：

| 变量 | 说明 |
|------|------|
| PYTICKTICK_V2_USERNAME | 滴答清单账号 |
| PYTICKTICK_V2_PASSWORD | 滴答清单密码 |
| DINGTALK_APP_KEY | 钉钉应用 Key |
| DINGTALK_APP_SECRET | 钉钉应用 Secret |
| DINGTALK_USER_ID | 钉钉 userid |
| DINGTALK_CORP_ID | 企业 CorpId（用于生成跳转链接） |

滴答清单需使用 v2 API（https://api.dida365.com/api/v2/）。钉钉参数见 [钉钉开放平台](https://open.dingtalk.com/)。

## 用法

```bash
# 默认昨天
python ticktick_focus.py

# 指定日期
python ticktick_focus.py 2026-03-04

# 填入日记 + 推送钉钉
python ticktick_focus.py -d --dingtalk
```

## 开机自动运行

详见 [docs/安装计划任务.md](docs/安装计划任务.md)。

## 依赖

- [pyticktick](https://github.com/sebpretzer/pyticktick) - TickTick/滴答清单 Python 客户端
- [钉钉开放平台 - 保存日志内容](https://open.dingtalk.com/document/development/save-custom-log-content)

## License

MIT
