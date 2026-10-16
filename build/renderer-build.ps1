param([switch]$Profile,[string]$OutputHost='',[switch]$SkipProbe,[switch]$HostOnly)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneTools=Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if(-not $OutputHost) {$OutputHost=Join-Path $PSScriptRoot 'runtime/pfe.swf'}
$OutputHost=[IO.Path]::GetFullPath($OutputHost)
if(-not $OutputHost.StartsWith($PSScriptRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Output must stay inside ContinuousScene/build'}
if($Profile -and $OutputHost -ne (Join-Path $PSScriptRoot 'runtime/pfe.swf')) {throw 'Profiling uses the isolated runtime only'}
New-Item -ItemType Directory -Force -Path (Split-Path $OutputHost) | Out-Null
$sceneBaseline=Join-Path $PSScriptRoot 'cache/v07-baseline/pfe.swf'
$sceneExpected='08A96759720C7A2AA489FCEEDB209C6E704500FDE7B1A4A49146BD578E99A8BC'
if(-not(Test-Path -LiteralPath $sceneBaseline)) {
    if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'pfe.swf')).Hash -ne $sceneExpected) {throw 'Installed host changed; inspect before freezing'}
    New-Item -ItemType Directory -Force -Path (Split-Path $sceneBaseline) | Out-Null
    Copy-Item -LiteralPath (Join-Path $sceneRoot 'pfe.swf') -Destination $sceneBaseline
}
if((Get-FileHash -LiteralPath $sceneBaseline).Hash -ne $sceneExpected) {throw 'Frozen host changed'}
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    if($Profile) {
        & $scenePython (Join-Path $PSScriptRoot 'profile-loading.py')
        if($LASTEXITCODE -ne 0) {throw 'Profiling preparation failed'}
        $sceneInput=Join-Path $PSScriptRoot 'generated/load-profile/host'
    } else {
        $sceneInput=Join-Path $PSScriptRoot 'generated/renderer-only'
        New-Item -ItemType Directory -Force -Path (Join-Path $sceneInput 'fe/graph') | Out-Null
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/scripts/fe/graph/Grafon.as') -Destination (Join-Path $sceneInput 'fe/graph/Grafon.as') -Force
    }
    & $sceneJava '-Xmx1400m' '-jar' (Join-Path $sceneTools 'ffdec/ffdec-cli.jar') '-importScript' $sceneBaseline $OutputHost $sceneInput
    if($LASTEXITCODE -ne 0) {throw 'Renderer compilation failed'}
    if($Profile -and -not $HostOnly) {
        $sceneWallSource=Join-Path $PSScriptRoot 'generated/load-profile/wb'
        & $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneTools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneTools 'flexsdk/frameworks')) '+configname=air' ('-load-config='+(Join-Path $sceneWallSource 'air-config.xml')) ('-source-path='+$sceneWallSource) ('-output='+(Join-Path $PSScriptRoot 'runtime/mods/WallBlend/release/WallBlendMod.swf')) (Join-Path $sceneWallSource 'WallBlendDoc.as')
        if($LASTEXITCODE -ne 0) {throw 'Wall profiler compilation failed'}
    }
    if(-not $SkipProbe) { & (Join-Path $PSScriptRoot 'build.ps1') -ProbeOnly }
} finally {$sceneLock.Dispose()}
