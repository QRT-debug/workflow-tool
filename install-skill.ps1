param(
    # 安装目标：Both 表示 Codex 和 WorkBuddy 都装，默认即 Both。
    [ValidateSet("Both", "Codex", "WorkBuddy")]
    [string]$Targets = "Both"
)

$ErrorActionPreference = "Stop"

$templateRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceSkillDir = Join-Path $templateRoot "skill\project-handoff-resume"

if (-not (Test-Path $sourceSkillDir)) {
    throw "Skill source not found: $sourceSkillDir"
}

function Get-AgentSkillRoot {
    # 返回指定智能体的技能根目录。
    # CODEX_HOME 是 Codex 官方支持的环境变量，可以放心当覆盖用。
    # WORKBUDDY_HOME 不是 WorkBuddy 的官方变量，WorkBuddy 始终只读 ~/.workbuddy/skills，
    # 这里的支持仅为本脚本自测留的口子；设置它会让安装位置偏离 WorkBuddy 的实际读取位置。
    param([string]$Agent)

    if ($Agent -eq "Codex") {
        $homeDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
        return Join-Path $homeDir "skills"
    }

    $homeDir = if ($env:WORKBUDDY_HOME) { $env:WORKBUDDY_HOME } else { Join-Path $HOME ".workbuddy" }
    return Join-Path $homeDir "skills"
}

# 展开目标列表：Both 时同时安装到两个智能体。
$resolvedTargets = switch ($Targets) {
    "Codex" { @("Codex") }
    "WorkBuddy" { @("WorkBuddy") }
    default { @("Codex", "WorkBuddy") }
}

$installed = @()

foreach ($agent in $resolvedTargets) {
    $skillsDir = Get-AgentSkillRoot -Agent $agent
    $targetSkillDir = Join-Path $skillsDir "project-handoff-resume"

    New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

    if (Test-Path $targetSkillDir) {
        Remove-Item -Recurse -Force -LiteralPath $targetSkillDir
    }

    Copy-Item -Recurse -Force -Path $sourceSkillDir -Destination $targetSkillDir
    $installed += "  [$agent] $targetSkillDir"
}

Write-Host "Installed skill to:"
foreach ($line in $installed) {
    Write-Host $line
}

Write-Host ""
Write-Host "Both agents share this single skill source, so the two copies stay identical."
Write-Host "Next step: initialize a project with init-project.ps1"
