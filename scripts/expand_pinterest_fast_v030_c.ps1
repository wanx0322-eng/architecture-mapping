param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$RawTarget = 2200
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Extractor = Get-Content -LiteralPath (Join-Path $Root "assets\pinterest_extract_v030.js") -Raw
$Base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Extractor))
$Codes = ($Base64.ToCharArray() | ForEach-Object { [int][char]$_ }) -join ','
$Expression = "eval(atob(String.fromCharCode($Codes)))"
$Subjects = @(
    "landscape architecture thesis", "landscape architecture studio", "landscape architecture award",
    "landscape architecture student competition", "landscape architecture professional competition",
    "landscape architecture portfolio", "landscape architecture presentation", "landscape architecture panel",
    "landscape architecture board", "landscape architecture graphics", "landscape architecture visualisation",
    "landscape architecture diagrammatic masterplan", "landscape architecture analytical masterplan",
    "landscape architecture site study", "landscape architecture site research",
    "landscape architecture precedent analysis", "landscape architecture design research",
    "landscape architecture system diagram", "landscape architecture network diagram",
    "landscape architecture framework diagram", "landscape architecture phasing diagram",
    "landscape architecture seasonal diagram", "landscape architecture time diagram",
    "landscape architecture sensory analysis", "landscape architecture experiential mapping",
    "landscape architecture movement mapping", "landscape architecture program diagram",
    "landscape architecture spatial diagram", "landscape architecture terrain model",
    "landscape architecture contour analysis", "landscape architecture planting strategy",
    "landscape architecture material strategy", "landscape architecture water strategy",
    "landscape architecture ecological strategy", "landscape architecture social strategy",
    "landscape architecture urban strategy", "landscape architecture regional strategy",
    "landscape architecture rural strategy", "landscape architecture conservation strategy",
    "landscape architecture restoration strategy", "landscape architecture regeneration strategy",
    "landscape architecture adaptive reuse", "landscape architecture infrastructure diagram",
    "landscape architecture public realm", "landscape architecture open space network",
    "landscape architecture green network", "landscape architecture river system",
    "landscape architecture coastal system", "landscape architecture wetland system",
    "landscape architecture biodiversity system"
)
$Suffixes = @("diagram", "analysis board", "competition board", "portfolio page", "axonometric diagram", "mapping")
$Queries = foreach ($Subject in $Subjects) { foreach ($Suffix in $Suffixes) { "$Subject $Suffix" } }
$Seen = @{}
if (Test-Path -LiteralPath $Output) {
    Get-Content -LiteralPath $Output | ForEach-Object {
        if ($_.Trim()) { $item = $_ | ConvertFrom-Json; if ($item.pin_id) { $Seen[[string]$item.pin_id] = $true } }
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
Write-Output "third_expansion_complete raw=$($Seen.Count) target=$RawTarget"
