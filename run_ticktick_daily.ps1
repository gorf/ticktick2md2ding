# 每日定时运行：取昨天数据，写日记 + 钉钉；开机（若已过1点）运行一次
# 用法：用计划任务调用本脚本。或手动运行： .\run_ticktick_daily.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MarkerFile = Join-Path $ScriptDir ".last_ticktick_run"
$LogFile = Join-Path $ScriptDir ".last_ticktick_run.log"

# 计划任务环境下 PATH 可能不含 Python，按顺序尝试 python / py
$PythonExe = $null
$PythonArgs = @("ticktick_focus.py", "-d", "--dingtalk")
foreach ($py in @("python", "py")) {
    try {
        $info = Get-Command $py -ErrorAction Stop
        $PythonExe = $info.Source
        if ($py -eq "py") { $PythonArgs = @("-3") + $PythonArgs }
        break
    } catch { }
}
if (-not $PythonExe) {
    $msg = "未找到 Python，请确保已安装并加入 PATH。时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $msg | Out-File -FilePath $LogFile -Encoding utf8
    exit 1
}

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
    & $PythonExe @PythonArgs
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $MarkerFile -Value $Yesterday -NoNewline
        "OK $Yesterday $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogFile -Encoding utf8
    } else {
        "EXIT $LASTEXITCODE $Yesterday $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogFile -Encoding utf8
    }
} catch {
    "ERROR: $_ $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $LogFile -Encoding utf8
    exit 1
}
