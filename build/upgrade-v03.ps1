param([string]$Evidence='release-v03-final',[Parameter(Mandatory=$true)][string]$WallEvidence)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$Evidence)
$sceneResult=Get-Content -LiteralPath (Join-Path $sceneEvidence 'result.json') -Raw | ConvertFrom-Json
if(-not $sceneResult.ok -or $sceneResult.mode -ne 'full' -or -not $sceneResult.preload -or $sceneResult.assertions.Count -lt 48 -or @($sceneResult.assertions | Where-Object {-not $_.ok}).Count) {throw 'Full preloaded runtime gate is not green'}
foreach($sceneCheck in @('whole-map-ready-before-play','walk-does-not-regenerate-map','distant-raster-untouched-by-local-combat','resaved-slot-retains-damage')) {
    if(-not @($sceneResult.assertions | Where-Object {$_.name -eq $sceneCheck -and $_.ok}).Count) {throw ('Missing gate '+$sceneCheck)}
}
$sceneWall=Get-Content -LiteralPath $WallEvidence -Raw | ConvertFrom-Json
$sceneWallProvenance=Get-Content -LiteralPath (Join-Path (Split-Path $WallEvidence) 'provenance.json') -Raw | ConvertFrom-Json
if(-not $sceneWall.passed -or $sceneWallProvenance.ModSHA256 -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'mods/WallBlend/release/WallBlendMod.swf')).Hash -or $sceneWallProvenance.GameSHA256 -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'pfe.swf')).Hash) {throw 'Wall regression is not green for these exact bytes'}
$sceneVision=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'generated/vision-checks/result.json') -Raw | ConvertFrom-Json
if(@($sceneVision).Count -ne 3 -or @($sceneVision | Where-Object {-not $_.passed}).Count) {throw 'Vision regression is not green'}
if(Select-String -LiteralPath (Join-Path $PSScriptRoot 'generated/rv-production/RealisticVisionMod.as') -Pattern 'sceneTimings' -Quiet) {throw 'Do not deploy timing-instrumented source'}
$sceneAudit=Get-Content -LiteralPath (Join-Path $sceneEvidence 'bytecode-audit.json') -Raw | ConvertFrom-Json
if(-not $sceneAudit.passed -or $sceneAudit.unchangedNamedMethodsAndInitializers -ne 4665) {throw 'Bytecode audit failed'}
$sceneHashes=@(Get-Content -LiteralPath (Join-Path $sceneEvidence 'build-hashes.json') -Raw | ConvertFrom-Json)+@(Get-Content -LiteralPath (Join-Path $sceneEvidence 'loaded-module-hashes.json') -Raw | ConvertFrom-Json)
foreach($sceneHash in $sceneHashes) {if((Get-FileHash -LiteralPath $sceneHash.Path).Hash -ne $sceneHash.Hash) {throw ('Tested file changed: '+$sceneHash.Path)}}
# Manifest is a shared deployment asset. Preserve it byte-for-byte, including new modules.
$sceneManifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
$sceneProductionRows=@(Get-Content -LiteralPath $sceneManifest | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'})
$sceneTestRows=@(Get-Content -LiteralPath (Join-Path $sceneRuntime 'mods/loader-manifest.txt') | Where-Object {$_ -notmatch '^ContinuousSceneProbe\|'})
if(@(Compare-Object $sceneProductionRows $sceneTestRows).Count) {throw 'Installed module set differs from tested set'}
foreach($sceneLine in $sceneProductionRows) {
    $sceneFields=$sceneLine.Split('|')
    if($sceneFields[0] -in 'ContinuousScene','RealisticVision','WallBlend') {continue}
    $sceneRelative='mods/'+$sceneFields[0]+'/release/'+$sceneFields[1]+'.swf'
    if((Get-FileHash -LiteralPath (Join-Path $sceneRoot $sceneRelative)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime $sceneRelative)).Hash) {throw ('Installed module changed: '+$sceneFields[0])}
}
$sceneFiles=@(
    @{relative='pfe.swf';before='8737D543B1F0256335766422705A54D0B345CA543C36918071E3B397155CECC9'},
    @{relative='mods/ContinuousScene/release/ContinuousSceneMod.swf';before='C8815042E2D8F2A14FFD8CC273604CD8B77CE6036F7875A2A04A705B0696C2E9'},
    @{relative='mods/RealisticVision/release/RealisticVisionMod.swf';before='ED76EC15666FD8CD50ACF0149F7EC32F2602D2E68D753580A0EC5814B95A2E99'},
    @{relative='mods/WallBlend/release/WallBlendMod.swf';before='44EFA2DBA4925260F3485EEDE9DAC1BDA81BE239485CBEADA670F61FD9C43ADA'}
)
foreach($sceneFile in $sceneFiles) {
    $sceneFile.target=Join-Path $sceneRoot $sceneFile.relative
    $sceneFile.source=Join-Path $sceneRuntime $sceneFile.relative
    if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.before) {throw ('Production baseline changed: '+$sceneFile.relative)}
    $sceneFile.after=(Get-FileHash -LiteralPath $sceneFile.source).Hash
}
if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'mods/ContinuousScene/release/scene.xml')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousScene/release/scene.xml')).Hash) {throw 'This upgrade must preserve the tested scene definition'}
$sceneStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sceneBackupDir=Join-Path $PSScriptRoot ('backups/upgrade-v03-'+$sceneStamp)
if(Test-Path -LiteralPath $sceneBackupDir) {throw 'Backup already exists'}
New-Item -ItemType Directory -Path $sceneBackupDir | Out-Null
foreach($sceneFile in $sceneFiles) {
    $sceneFile.backup=if($sceneFile.relative -eq 'pfe.swf') {Join-Path $sceneRoot ('pfe_before_ContinuousScene_v03_'+$sceneStamp+'.swf')} else {Join-Path $sceneBackupDir (Split-Path $sceneFile.target -Leaf)}
    if(Test-Path -LiteralPath $sceneFile.backup) {throw 'Refusing to overwrite backup'}
    Copy-Item -LiteralPath $sceneFile.target -Destination $sceneFile.backup
    if((Get-FileHash -LiteralPath $sceneFile.backup).Hash -ne $sceneFile.before) {throw 'Backup validation failed'}
}
$sceneManifestHash=(Get-FileHash -LiteralPath $sceneManifest).Hash
try {
    foreach($sceneFile in $sceneFiles) {
        Copy-Item -LiteralPath $sceneFile.source -Destination $sceneFile.target -Force
        if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.after) {throw 'Deployment hash mismatch'}
    }
    if((Get-FileHash -LiteralPath $sceneManifest).Hash -ne $sceneManifestHash) {throw 'Manifest changed during upgrade'}
    $sceneReceipt=[ordered]@{version='0.3.0';installed=(Get-Date).ToString('o');evidence=$Evidence;hostHash=$sceneFiles[0].after;manifestHash=$sceneManifestHash;files=$sceneFiles;wallEvidence=$WallEvidence}
    $sceneReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'upgrade-receipt.json') -Encoding UTF8
    $sceneReceipt | ConvertTo-Json -Depth 5
} catch {
    foreach($sceneFile in $sceneFiles) {Copy-Item -LiteralPath $sceneFile.backup -Destination $sceneFile.target -Force}
    throw
}
