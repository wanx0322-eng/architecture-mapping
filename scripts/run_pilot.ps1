param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [int]$Target = 100
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = "C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$Dataset = Join-Path $Root "dataset"
$Capture = Join-Path $Dataset "raw\captured.jsonl"

& (Join-Path $PSScriptRoot "collect_pinterest.ps1") -TabId $TabId -Output $Capture -Target $Target
& $Python (Join-Path $PSScriptRoot "pipeline.py") ingest --root $Dataset --input $Capture
& $Python (Join-Path $PSScriptRoot "pipeline.py") thumbnails --root $Dataset
& $Python (Join-Path $PSScriptRoot "pipeline.py") dedupe --root $Dataset
& $Python (Join-Path $PSScriptRoot "pipeline.py") core-queue --root $Dataset --limit $Target

Write-Output "Pilot collection prepared. Multimodal analysis queue: $Dataset\raw\core_queue.jsonl"

