param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$RawTarget = 2400
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Extractor = Get-Content -LiteralPath (Join-Path $Root "assets\pinterest_extract_v030.js") -Raw
$Base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Extractor))
$Codes = ($Base64.ToCharArray() | ForEach-Object { [int][char]$_ }) -join ','
$Expression = "eval(atob(String.fromCharCode($Codes)))"
$Subjects = @(
    "urban park", "linear park", "waterfront park", "river restoration", "wetland park",
    "ecological corridor", "greenway", "stormwater park", "sponge city", "resilient landscape",
    "brownfield landscape", "post industrial landscape", "campus open space", "community park",
    "public plaza", "streetscape", "urban forest", "habitat restoration", "coastal landscape",
    "floodplain landscape", "agricultural landscape", "cultural landscape", "heritage landscape",
    "memorial landscape", "botanical garden", "roof landscape", "productive landscape",
    "play landscape", "healing landscape", "transport landscape", "infrastructure landscape",
    "regional landscape", "territorial landscape", "landscape urbanism", "environmental design",
    "urban ecology", "landscape planning", "site planning", "open space planning", "master planning"
)
$Formats = @(
    "analysis board",
    "design development diagram",
    "strategy mapping",
    "competition panel",
    "portfolio board",
    "section diagram",
    "system axonometric",
    "concept evolution"
)
$Queries = foreach ($Subject in $Subjects) {
    foreach ($Format in $Formats) { "$Subject landscape architecture $Format" }
}
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
foreach ($Query in ($Queries | Select-Object -Unique)) {
    $Index++
    if ($Seen.Count -ge $RawTarget) { break }
    $Url = "https://jp.pinterest.com/search/pins/?q=$([Uri]::EscapeDataString($Query))"
    npx.cmd -y bb-browser goto $Url --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) { break }
    Start-Sleep -Milliseconds 800
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
Write-Output "second_expansion_complete raw=$($Seen.Count) target=$RawTarget"
