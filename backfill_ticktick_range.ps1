# 按日期范围补跑 TickTick → 日记（可选钉钉）
# 用法（在 PowerShell 中）：
#   cd "...\ticktick2md2ding"
#   .\backfill_ticktick_range.ps1
#   .\backfill_ticktick_range.ps1 -StartDate 2026-04-16 -EndDate 2026-05-08
#   .\backfill_ticktick_range.ps1 -StartDate 2026-04-16 -EndDate 2026-05-08 -NoDingtalk
#
# 需同目录存在 .env（PYTICKTICK_V2_USERNAME / PYTICKTICK_V2_PASSWORD）及 ticktick_focus.py

param(
    [string]$StartDate = "2026-04-16",
    [string]$EndDate = "2026-05-08",
    [switch]$NoDingtalk
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonExe = $null
$UsePyLauncher = $false
foreach ($c in @("python", "py")) {
    try {
        $PythonExe = (Get-Command $c -ErrorAction Stop).Source
        if ($c -eq "py") { $UsePyLauncher = $true }
        break
    } catch { }
}
if (-not $PythonExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) {
            $PythonExe = $p
            break
        }
    }
}
if (-not $PythonExe) {
    Write-Error "未找到 python。请安装 Python 并加入 PATH，或把本机 python.exe 路径写进脚本 `$PythonExe 回退列表。"
    exit 1
}

$s = [datetime]::ParseExact($StartDate, "yyyy-MM-dd", $null)
$e = [datetime]::ParseExact($EndDate, "yyyy-MM-dd", $null)
if ($s -gt $e) {
    Write-Error "StartDate 不能晚于 EndDate"
    exit 1
}

$d = $s
while ($d -le $e) {
    $ds = $d.ToString("yyyy-MM-dd")
    Write-Host ">>> $ds"
    $pyArgs = @("ticktick_focus.py", $ds, "-d")
    if (-not $NoDingtalk) { $pyArgs += "--dingtalk" }
    if ($UsePyLauncher) {
        $full = @("-3") + $pyArgs
        & $PythonExe @full
    } else {
        & $PythonExe @pyArgs
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "退出码 $LASTEXITCODE : $ds"
    }
    $d = $d.AddDays(1)
}

Write-Host "完成。范围: $StartDate .. $EndDate"
