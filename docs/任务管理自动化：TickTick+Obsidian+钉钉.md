# 任务管理自动化：TickTick + Obsidian + 钉钉

> 用 Python 脚本打通滴答清单、Obsidian 日记和钉钉工作日志，实现专注记录与日报的一键生成。

## 一、任务管理流程

- **滴答清单（TickTick）**：记任务、番茄、专注记录与想法
- **Obsidian**：日记、笔记
- **钉钉**：工作日志

## 二、脚本功能

1. **TickTick 拉数据**：pomodoros 专注记录、closed 完成任务
2. **同任务合并**：按任务名汇总时长，去重完成任务
3. **写 Obsidian 日记**：`--diary` 填入模板
4. **推钉钉**：savecontent 预填，生成跳转链接
5. **开机补跑**：PowerShell + 计划任务

## 三、配置与使用

见 [README](../README.md) 及 [安装计划任务](安装计划任务.md)。

## 四、参考资料

- [pyticktick](https://github.com/sebpretzer/pyticktick)
- [钉钉 - 保存日志内容](https://open.dingtalk.com/document/development/save-custom-log-content)
- [钉钉日志接口使用案例](https://dingtalk.apifox.cn/doc-392425)
