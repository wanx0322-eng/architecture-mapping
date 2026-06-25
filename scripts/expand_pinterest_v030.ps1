param(
    [Parameter(Mandatory=$true)][string]$TabId,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$RawTarget = 3000
)

$ErrorActionPreference = "Stop"
$Queries = @(
    "landscape architecture diagram",
    "landscape site analysis",
    "landscape architecture mapping",
    "landscape architecture competition board",
    "landscape strategy diagram",
    "landscape circulation diagram",
    "landscape ecology diagram",
    "ecological site analysis diagram",
    "green infrastructure mapping",
    "blue green network diagram",
    "watershed landscape analysis",
    "hydrology landscape diagram",
    "topography landscape analysis",
    "vegetation analysis landscape architecture",
    "landscape section analysis",
    "landscape axonometric diagram",
    "exploded landscape axonometric",
    "landscape design process diagram",
    "landscape concept diagram",
    "landscape masterplan analysis",
    "urban landscape analysis diagram",
    "urban design mapping",
    "urban analysis diagram",
    "urban morphology mapping",
    "figure ground urban analysis",
    "public space activity mapping",
    "behavior mapping landscape architecture",
    "pedestrian flow landscape architecture",
    "site circulation landscape",
    "site constraints opportunities landscape",
    "site synthesis diagram landscape",
    "climate analysis landscape architecture",
    "sun wind site analysis",
    "noise analysis landscape architecture",
    "land use analysis urban design",
    "connectivity analysis urban design",
    "riverfront landscape analysis",
    "waterfront landscape diagram",
    "park design analysis diagram",
    "campus landscape analysis",
    "community landscape mapping",
    "density analysis urban design",
    "spatial sequence landscape diagram",
    "layered mapping landscape architecture",
    "landscape architecture presentation board",
    "landscape architecture portfolio diagram",
    "ASLA competition board analysis",
    "IFLA landscape competition board",
    "landscape architecture hand drawn diagram",
    "landscape collage diagram",
    "landscape watercolor analysis",
    "landscape architecture vector diagram",
    "landscape architecture graphic analysis",
    "landscape architecture zoning diagram",
    "landscape architecture bubble diagram",
    "landscape architecture user analysis",
    "landscape architecture pavement diagram",
    "landscape architecture planting diagram",
    "landscape architecture material palette",
    "landscape architecture design evolution"
)

$Index = 0
foreach ($Query in $Queries) {
    $Index++
    $Current = if (Test-Path -LiteralPath $Output) { (Get-Content -LiteralPath $Output | Where-Object { $_.Trim() }).Count } else { 0 }
    if ($Current -ge $RawTarget) { break }
    $Encoded = [Uri]::EscapeDataString($Query)
    $Url = "https://jp.pinterest.com/search/pins/?q=$Encoded"
    Write-Output "query=$Index/$($Queries.Count) raw_before=$Current term=$Query"
    npx.cmd -y bb-browser goto $Url --tab $TabId --json | Out-Null
    if ($LASTEXITCODE -ne 0) { break }
    Start-Sleep -Milliseconds 1400
    & (Join-Path $PSScriptRoot "collect_pinterest_v030.ps1") `
        -TabId $TabId -Output $Output -Target $RawTarget `
        -MaxEmptyRounds 3 -ScrollPixels 2200 -WaitMilliseconds 900
}

$Final = if (Test-Path -LiteralPath $Output) { (Get-Content -LiteralPath $Output | Where-Object { $_.Trim() }).Count } else { 0 }
Write-Output "expansion_capture_complete raw=$Final target=$RawTarget"
