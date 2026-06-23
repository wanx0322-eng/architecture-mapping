param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [string]$Output = "dataset\raw\captured.jsonl",
    [int]$Target = 100,
    [int]$MaxEmptyRounds = 5,
    [int]$ScrollPixels = 1800,
    [int]$WaitMilliseconds = 1800
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $PSScriptRoot
$Extractor = Get-Content -LiteralPath (Join-Path $SkillRoot "assets\pinterest_extract.js") -Raw
$Base64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Extractor))
$Codes = ($Base64.ToCharArray() | ForEach-Object { [int][char]$_ }) -join ','
$Expression = "eval(atob(String.fromCharCode($Codes)))"
$OutputPath = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $SkillRoot $Output }
$OutputDir = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$env:npm_config_cache = "F:\Ai_porject_codex\tmp\npm-cache"

$Seen = @{}
if (Test-Path -LiteralPath $OutputPath) {
    Get-Content -LiteralPath $OutputPath | ForEach-Object {
        if ($_.Trim()) {
            $item = $_ | ConvertFrom-Json
            $key = if ($item.pin_id) { [string]$item.pin_id } else { [string]$item.pin_url }
            $Seen[$key] = $true
        }
    }
}

$EmptyRounds = 0
while ($Seen.Count -lt $Target -and $EmptyRounds -lt $MaxEmptyRounds) {
    $Raw = npx.cmd -y bb-browser eval $Expression --tab $TabId --json
    $Parsed = $Raw | ConvertFrom-Json
    $Batch = $Parsed.result.result
    $Added = 0
    foreach ($item in @($Batch)) {
        $key = if ($item.pin_id) { [string]$item.pin_id } else { [string]$item.pin_url }
        if (-not $key -or $Seen.ContainsKey($key)) { continue }
        $item | ConvertTo-Json -Compress -Depth 8 | Add-Content -LiteralPath $OutputPath -Encoding utf8
        $Seen[$key] = $true
        $Added++
    }
    if ($Added -eq 0) { $EmptyRounds++ } else { $EmptyRounds = 0 }
    Write-Output "captured=$($Seen.Count) added=$Added empty_rounds=$EmptyRounds"
    if ($Seen.Count -ge $Target) { break }
    $ScrollExpression = "window.scrollBy(0,$ScrollPixels);document.documentElement.scrollTop"
    npx.cmd -y bb-browser eval $ScrollExpression --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Scroll failed; preserving collected records and stopping for browser recovery."
        break
    }
    Start-Sleep -Milliseconds $WaitMilliseconds
}

if ($EmptyRounds -ge $MaxEmptyRounds) {
    Write-Warning "Stopped after $MaxEmptyRounds rounds without new visible Pins. Check login, CAPTCHA, or end of results."
}
