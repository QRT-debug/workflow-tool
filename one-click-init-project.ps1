param(
    [string]$ProjectPath = "C:\Users\Admin\Desktop\你的项目"
)

$ErrorActionPreference = "Stop"

$templateRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$initScript = Join-Path $templateRoot "init-project.ps1"

if (-not (Test-Path $initScript)) {
    throw "init-project.ps1 not found: $initScript"
}

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    throw "ProjectPath is empty. Edit the default value or pass -ProjectPath."
}

if ($ProjectPath -eq "C:\Users\Admin\Desktop\你的项目") {
    Write-Host "You are still using the placeholder path."
    Write-Host "Edit the ProjectPath value at the top of one-click-init-project.ps1"
    Write-Host "or run:"
    Write-Host 'powershell -ExecutionPolicy Bypass -File .\one-click-init-project.ps1 -ProjectPath "C:\path\to\your\repo"'
    exit 1
}

# 直接在当前 PowerShell 里调用同目录的脚本：
# 不依赖 PATH 上存在 powershell.exe，输出留在同一个控制台，异常也能正常抛出。
& $initScript -ProjectPath $ProjectPath
