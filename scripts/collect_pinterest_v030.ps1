param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$Target = 3000,
    [int]$MaxEmptyRounds = 5,
    [int]$ScrollPixels = 2200,
    [int]$WaitMilliseconds = 1000
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Extractor = Get-Content -LiteralPath (Join-Path $Root "assets\pinterest_extract_v030.js") -Raw
$Base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Extractor))
$Codes = ($Base64.ToCharArray() | ForEach-Object { [int][char]$_ }) -join ','
$Expression = "eval(atob(String.fromCharCode($Codes)))"
$OutputDir = Split-Path -Parent $Output
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$Seen = @{}
if (Test-Path -LiteralPath $Output) {
    Get-Content -LiteralPath $Output | ForEach-Object {
        if ($_.Trim()) {
            $item = $_ | ConvertFrom-Json
            if ($item.pin_id) { $Seen[[string]$item.pin_id] = $true }
        }
    }
}

$EmptyRounds = 0
while ($Seen.Count -lt $Target -and $EmptyRounds -lt $MaxEmptyRounds) {
    $Raw = npx.cmd -y bb-browser eval $Expression --tab $TabId --json
    $Parsed = $Raw | ConvertFrom-Json
    $Added = 0
    foreach ($item in @($Parsed.result.result)) {
        $key = [string]$item.pin_id
        if (-not $key -or $Seen.ContainsKey($key)) { continue }
        $item | ConvertTo-Json -Compress -Depth 8 | Add-Content -LiteralPath $Output -Encoding utf8
        $Seen[$key] = $true
        $Added++
    }
    if ($Added -eq 0) { $EmptyRounds++ } else { $EmptyRounds = 0 }
    Write-Output "captured=$($Seen.Count) added=$Added empty_rounds=$EmptyRounds"
    if ($Seen.Count -ge $Target) { break }
    npx.cmd -y bb-browser eval "window.scrollBy(0,$ScrollPixels);document.documentElement.scrollTop" --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) { break }
    Start-Sleep -Milliseconds $WaitMilliseconds
}
