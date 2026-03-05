# 每日定时运行：取昨天数据，写日记 + 钉钉；开机（若已过1点）运行一次
# 用法：用计划任务调用本脚本。或手动运行： .\run_ticktick_daily.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MarkerFile = Join-Path $ScriptDir ".last_ticktick_run"

$Yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
$Now = Get-Date

# 仅当当前时间 >= 1:00 时才执行
if ($Now.Hour -lt 1) {
    exit 0
}

# 避免同一天重复跑
if (Test-Path $MarkerFile) {
    $Last = Get-Content $MarkerFile -Raw
    if ($Last -eq $Yesterday) {
        exit 0
    }
}

Set-Location $ScriptDir
try {
    & python ticktick_focus.py -d --dingtalk
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $MarkerFile -Value $Yesterday -NoNewline
    }
} finally {
}
