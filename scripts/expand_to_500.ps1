param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [int]$RawTarget = 600
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Capture = Join-Path $Root "dataset\raw\captured.jsonl"
$Queries = @(
    "architectural site analysis", "landscape site analysis board", "urban design mapping",
    "architecture circulation diagram", "landscape architecture mapping", "urban analysis diagram",
    "site analysis architecture presentation", "landscape architecture diagram board", "masterplan analysis diagram",
    "architectural concept diagram", "massing evolution diagram", "exploded axonometric architecture",
    "exploded landscape axonometric", "urban morphology mapping", "figure ground urban analysis",
    "pedestrian flow analysis architecture", "site circulation landscape", "green infrastructure mapping",
    "ecological site analysis diagram", "watershed landscape analysis", "topography analysis architecture",
    "climate analysis architecture", "sun wind site analysis", "noise analysis architecture",
    "land use analysis urban", "public space activity mapping", "behavior mapping architecture",
    "historical urban mapping", "heritage mapping architecture", "spatial sequence diagram architecture",
    "program diagram architecture", "landscape strategy diagram", "urban design strategy diagram",
    "competition architecture analysis board", "architecture portfolio analysis diagram",
    "landscape architecture competition board", "urban design competition panel",
    "site synthesis diagram architecture", "site constraints opportunities diagram",
    "swot site analysis architecture", "connectivity analysis urban design",
    "transportation network analysis urban", "blue green network diagram", "ecological corridor mapping",
    "riverfront analysis architecture", "waterfront urban design diagram", "park design analysis diagram",
    "campus masterplan analysis", "community mapping architecture", "density analysis urban design",
    "typology mapping architecture", "axonometric site analysis", "layered mapping architecture",
    "architectural mapping diagram", "landscape mapping diagram", "city mapping diagram",
    "spatial mapping architecture", "infrastructure mapping landscape", "urban section analysis diagram",
    "landscape section analysis board", "site photos analysis architecture", "existing condition analysis landscape"
)

$env:npm_config_cache = "F:\Ai_porject_codex\tmp\npm-cache"
$Index = 0
foreach ($Query in $Queries) {
    $Index++
    $Current = if (Test-Path -LiteralPath $Capture) { (Get-Content -LiteralPath $Capture | Where-Object { $_.Trim() }).Count } else { 0 }
    if ($Current -ge $RawTarget) { break }
    $Encoded = [Uri]::EscapeDataString($Query)
    $Url = "https://jp.pinterest.com/search/pins/?q=$Encoded"
    Write-Output "query=$Index/$($Queries.Count) raw_before=$Current term=$Query"
    npx.cmd -y bb-browser goto $Url --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Navigation failed for query: $Query" }
    Start-Sleep -Milliseconds 1800
    & (Join-Path $PSScriptRoot "collect_pinterest.ps1") `
        -TabId $TabId -Output $Capture -Target $RawTarget `
        -MaxEmptyRounds 2 -ScrollPixels 2200 -WaitMilliseconds 900
}

$Final = if (Test-Path -LiteralPath $Capture) { (Get-Content -LiteralPath $Capture | Where-Object { $_.Trim() }).Count } else { 0 }
Write-Output "expansion_capture_complete raw=$Final target=$RawTarget"
