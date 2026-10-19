param([switch]$Profile)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneBaseline=Join-Path $PSScriptRoot 'cache/v08-baseline'
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneFfdec=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
$sceneExpected='2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA'
if(-not(Test-Path -LiteralPath $sceneBaseline)) {
    if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'pfe.swf')).Hash -ne $sceneExpected){throw 'Installed host changed; review before freezing'}
    New-Item -ItemType Directory -Path $sceneBaseline|Out-Null
    $sceneInputs=@('pfe.swf','mods/loader-manifest.txt')
    foreach($line in Get-Content (Join-Path $sceneRoot 'mods/loader-manifest.txt')) {
        if($line -notmatch '^[^#]+\|[^|]+\|1\|'){continue}
        $parts=$line.Split('|');$sceneInputs+=('mods/'+$parts[0]+'/release/'+$parts[1]+'.swf')
    }
    $sceneHashes=@()
    foreach($sceneRelative in $sceneInputs) {
        $source=Join-Path $sceneRoot $sceneRelative;$dest=Join-Path $sceneBaseline $sceneRelative
        New-Item -ItemType Directory -Force -Path (Split-Path $dest)|Out-Null
        Copy-Item -LiteralPath $source -Destination $dest
        $sceneHashes+=@{relative=$sceneRelative;sha256=(Get-FileHash -LiteralPath $dest).Hash}
    }
    $sceneHashes|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $sceneBaseline 'inputs.json') -Encoding utf8
}
if((Get-FileHash -LiteralPath (Join-Path $sceneBaseline 'pfe.swf')).Hash -ne $sceneExpected){throw 'Frozen host identity differs'}
$sceneLock=[IO.File]::Open((Join-Path $sceneRuntime 'session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    # Fresh production dependencies/configuration in the isolated application.
    & (Join-Path $PSScriptRoot 'test-mods.ps1') -AllMods
    Copy-Item -LiteralPath (Join-Path $sceneBaseline 'mods/ContinuousScene/release/ContinuousSceneMod.swf') -Destination (Join-Path $sceneRuntime 'mods/ContinuousScene/release/ContinuousSceneMod.swf') -Force
    if($Profile) {
        $sceneExport=Join-Path $PSScriptRoot 'cache/v08-native'
        if(-not(Test-Path -LiteralPath (Join-Path $sceneExport 'scripts/fe/loc/Location.as'))) {
            & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-selectclass' 'fe.loc.Location' '-export' 'script' $sceneExport (Join-Path $sceneBaseline 'pfe.swf')
            if($LASTEXITCODE -ne 0){throw 'Current Location export failed'}
        }
        & $scenePython (Join-Path $PSScriptRoot 'issues_profile.py')
        if($LASTEXITCODE -ne 0){throw 'Profile preparation failed'}
        & $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-importScript' (Join-Path $sceneBaseline 'pfe.swf') (Join-Path $sceneRuntime 'pfe.swf') (Join-Path $PSScriptRoot 'generated/issues-profile')
        if($LASTEXITCODE -ne 0){throw 'Isolated profile compilation failed'}
    }else{Copy-Item -LiteralPath (Join-Path $sceneBaseline 'pfe.swf') -Destination (Join-Path $sceneRuntime 'pfe.swf') -Force}
    & (Join-Path $PSScriptRoot 'build.ps1') -ProbeOnly
}finally{$sceneLock.Dispose()}
