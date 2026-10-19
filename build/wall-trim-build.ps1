param([switch]$NoRuntime,[string]$CandidateDirectory='candidate-v08-wall-trim')
$ErrorActionPreference='Stop'
if($CandidateDirectory -notmatch '^candidate-v08-wall-trim(-[a-z0-9]+)?$'){throw 'Candidate must remain inside this build directory'}
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneTools=Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
& $scenePython (Join-Path $PSScriptRoot 'wallblend_trim.py')
if($LASTEXITCODE -ne 0){throw 'Wall padding source preparation failed'}
$sceneSource=Join-Path $PSScriptRoot 'generated/wb-trim-source'
$sceneOutput=Join-Path $PSScriptRoot ($CandidateDirectory+'/WallBlendMod.swf')
New-Item -ItemType Directory -Force -Path (Split-Path $sceneOutput)|Out-Null
& $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneTools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneTools 'flexsdk/frameworks')) '+configname=air' ('-load-config='+(Join-Path $sceneSource 'air-config.xml')) ('-source-path='+$sceneSource) ('-output='+$sceneOutput) (Join-Path $sceneSource 'WallBlendDoc.as')
if($LASTEXITCODE -ne 0){throw 'Wall padding candidate compilation failed'}
if(-not $NoRuntime) {
    $sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
    try {Copy-Item -LiteralPath $sceneOutput -Destination (Join-Path $PSScriptRoot 'runtime/mods/WallBlend/release/WallBlendMod.swf') -Force}
    finally {$sceneLock.Dispose()}
}
Get-FileHash -LiteralPath $sceneOutput
