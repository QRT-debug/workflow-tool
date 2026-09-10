param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath
)

$ErrorActionPreference = "Stop"

$templateRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path $ProjectPath).Path

$sourcePrompt = Join-Path $templateRoot "templates\CODEX_PROJECT_PROMPT.md"
$sourceProjectMap = Join-Path $templateRoot "templates\docs\PROJECT_MAP.md"
$sourceHandoff = Join-Path $templateRoot "templates\docs\HANDOFF.md"

$targetPrompt = Join-Path $projectRoot "CODEX_PROJECT_PROMPT.md"
$targetDocsDir = Join-Path $projectRoot "docs"
$targetProjectMap = Join-Path $targetDocsDir "PROJECT_MAP.md"
$targetHandoff = Join-Path $targetDocsDir "HANDOFF.md"

New-Item -ItemType Directory -Force -Path $targetDocsDir | Out-Null

if (-not (Test-Path $targetPrompt)) {
    Copy-Item $sourcePrompt $targetPrompt
    Write-Host "Created: $targetPrompt"
} else {
    Write-Host "Skipped existing: $targetPrompt"
}

if (-not (Test-Path $targetProjectMap)) {
    Copy-Item $sourceProjectMap $targetProjectMap
    Write-Host "Created: $targetProjectMap"
} else {
    Write-Host "Skipped existing: $targetProjectMap"
}

if (-not (Test-Path $targetHandoff)) {
    Copy-Item $sourceHandoff $targetHandoff
    Write-Host "Created: $targetHandoff"
} else {
    Write-Host "Skipped existing: $targetHandoff"
}

Write-Host ""
Write-Host "Project templates are ready."
Write-Host "Fill them with project-specific content, then start a new chat in Codex or WorkBuddy with:"
Write-Host "使用 project-handoff-resume，然后继续这个工程。"
