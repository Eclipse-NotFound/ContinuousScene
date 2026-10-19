# Called by the candidate builder while it owns runtime/session.lock.
param([Parameter(Mandatory=$true)][string]$InputHost,[Parameter(Mandatory=$true)][string]$OutputHost)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$sceneFfdec=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
$sceneGen=Join-Path $PSScriptRoot 'generated/v08-objects'
foreach($scenePath in @($InputHost,$OutputHost)) {
    if(-not([IO.Path]::GetFullPath($scenePath).StartsWith($PSScriptRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase))){throw 'Object patch inputs and outputs must stay in CS/build'}
}
if(-not(Test-Path (Join-Path $PSScriptRoot 'cache/v08-objects/scripts/fe/loc/Location.as'))) {
    & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-selectclass' 'fe.serv.Interact,fe.loc.Bonus,fe.unit.Unit,fe.unit.UnitPlayer,fe.loc.Location' '-export' 'script' (Join-Path $PSScriptRoot 'cache/v08-objects') (Join-Path $PSScriptRoot 'cache/v08-baseline/pfe.swf')
    if($LASTEXITCODE -ne 0){throw 'Interact source export failed'}
}
& $scenePython (Join-Path $PSScriptRoot 'objects_native_patch.py')
if($LASTEXITCODE -ne 0){throw 'Interact source preparation failed'}
& $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-importScript' $InputHost (Join-Path $sceneGen 'donor.swf') (Join-Path $sceneGen 'source')
if($LASTEXITCODE -ne 0){throw 'Interact donor failed'}
foreach($sceneVariant in @('original','donor')) {
    $scenePcodeHost=if($sceneVariant -eq 'original'){$InputHost}else{Join-Path $sceneGen 'donor.swf'}
    & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-format' 'script:pcode' '-selectclass' 'fe.serv.Interact,fe.loc.Bonus,fe.unit.Unit,fe.unit.UnitPlayer,fe.loc.Location' '-export' 'script' (Join-Path $sceneGen ($sceneVariant+'-pcode')) $scenePcodeHost
    if($LASTEXITCODE -ne 0){throw 'Interact p-code export failed'}
}
& $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' $InputHost (Join-Path $sceneGen 'base.xml')
if($LASTEXITCODE -ne 0){throw 'Object base metadata failed'}
& $scenePython (Join-Path $PSScriptRoot 'objects_native_patch.py') 'plan'
if($LASTEXITCODE -ne 0){throw 'Object method plan failed'}
& $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-replace' $InputHost $OutputHost (Join-Path $sceneGen 'replace-args.txt')
if($LASTEXITCODE -ne 0){throw 'Object method transplant failed'}
