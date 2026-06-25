param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$RawTarget = 3000
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Extractor = Get-Content -LiteralPath (Join-Path $Root "assets\pinterest_extract_v030.js") -Raw
$Base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Extractor))
$Codes = ($Base64.ToCharArray() | ForEach-Object { [int][char]$_ }) -join ','
$Expression = "eval(atob(String.fromCharCode($Codes)))"

$Topics = @(
    "site", "urban", "park", "riverfront", "waterfront", "campus", "community",
    "ecological", "hydrology", "watershed", "topography", "vegetation", "habitat",
    "green infrastructure", "blue green", "climate", "stormwater", "wetland",
    "public space", "pedestrian", "circulation", "mobility", "land use", "zoning",
    "morphology", "figure ground", "activity", "behavior", "heritage", "resilience",
    "biodiversity", "planting", "pavement", "material", "terrain", "section"
)
$Forms = @(
    "landscape architecture analysis diagram",
    "landscape architecture mapping",
    "landscape architecture strategy diagram",
    "landscape architecture competition board",
    "landscape architecture axonometric",
    "landscape architecture presentation",
    "landscape architecture concept diagram",
    "landscape architecture process diagram"
)
$Queries = foreach ($Topic in $Topics) {
    foreach ($Form in $Forms) { "$Topic $Form" }
}
$Queries = $Queries | Select-Object -Unique

$Seen = @{}
if (Test-Path -LiteralPath $Output) {
    Get-Content -LiteralPath $Output | ForEach-Object {
        if ($_.Trim()) {
            $item = $_ | ConvertFrom-Json
            if ($item.pin_id) { $Seen[[string]$item.pin_id] = $true }
        }
    }
}

$Index = 0
foreach ($Query in $Queries) {
    $Index++
    if ($Seen.Count -ge $RawTarget) { break }
    $Url = "https://jp.pinterest.com/search/pins/?q=$([Uri]::EscapeDataString($Query))"
    npx.cmd -y bb-browser goto $Url --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) { break }
    Start-Sleep -Milliseconds 850
    $Raw = npx.cmd -y bb-browser eval $Expression --tab $TabId --json
    if ($LASTEXITCODE -ne 0) { break }
    $Parsed = $Raw | ConvertFrom-Json
    $Added = 0
    foreach ($item in @($Parsed.result.result)) {
        $key = [string]$item.pin_id
        if (-not $key -or $Seen.ContainsKey($key)) { continue }
        $item | ConvertTo-Json -Compress -Depth 8 | Add-Content -LiteralPath $Output -Encoding utf8
        $Seen[$key] = $true
        $Added++
    }
    Write-Output "query=$Index/$($Queries.Count) captured=$($Seen.Count) added=$Added term=$Query"
}
Write-Output "fast_expansion_complete raw=$($Seen.Count) target=$RawTarget"
