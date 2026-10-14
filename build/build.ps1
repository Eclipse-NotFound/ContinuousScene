param(
    [string]$Java = 'D:\Program Files\Adobe Animate 2024\jre\bin\java.exe',
    [string]$Python = 'C:\Users\hello\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
    [switch]$DriverOnly,
    [switch]$ProbeOnly,
    [string]$BaseHost = ''
)
$ErrorActionPreference = 'Stop'
$sceneRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneMod = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sceneTools = Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
$sceneFlex = Join-Path $sceneTools 'flexsdk'
if(-not $BaseHost) {$BaseHost=Join-Path $sceneRoot 'pfe.swf'}
$BaseHost=(Resolve-Path -LiteralPath $BaseHost).Path
if (-not $DriverOnly -and -not $ProbeOnly) {
    if((Get-FileHash -LiteralPath $BaseHost).Hash -ne 'C631CBF3511B6EE303F533D08D51511FE0EB702F43E5DB17F5241D8576C64867') {throw 'Choose the verified original host backup with -BaseHost'}
    & $Java '-Xmx1400m' '-jar' (Join-Path $sceneTools 'ffdec/ffdec-cli.jar') '-selectclass' 'MainFE,fe.loc.Game,fe.loc.Location,fe.graph.Grafon,fe.inter.Camera' `
        '-export' 'script' (Join-Path $PSScriptRoot 'cache/current-swf') $BaseHost
    if ($LASTEXITCODE -ne 0) { throw 'Current host source export failed' }
    & $Python (Join-Path $PSScriptRoot 'prepare.py') $BaseHost
    if ($LASTEXITCODE -ne 0) { throw 'Source preparation failed' }
    & $Java '-Xmx1400m' '-jar' (Join-Path $sceneTools 'ffdec/ffdec-cli.jar') '-importScript' `
        $BaseHost (Join-Path $PSScriptRoot 'generated/donor.swf') (Join-Path $PSScriptRoot 'generated/scripts')
    if ($LASTEXITCODE -ne 0) { throw 'Isolated host patch failed' }
    $sceneGrafonDir = Join-Path $PSScriptRoot 'generated/grafon-only/fe/graph'
    New-Item -ItemType Directory -Force -Path $sceneGrafonDir | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/scripts/fe/graph/Grafon.as') -Destination (Join-Path $sceneGrafonDir 'Grafon.as')
    & $Java '-Xmx1400m' '-jar' (Join-Path $sceneTools 'ffdec/ffdec-cli.jar') '-importScript' `
        $BaseHost (Join-Path $PSScriptRoot 'generated/grafon-host.swf') (Join-Path $PSScriptRoot 'generated/grafon-only')
    if ($LASTEXITCODE -ne 0) { throw 'Renderer donor failed' }
    $sceneFfdec = Join-Path $sceneTools 'ffdec/ffdec-cli.jar'
    foreach($sceneSourceSwf in @('original','donor')) {
        $sceneInput=if($sceneSourceSwf -eq 'original') {$BaseHost} else {Join-Path $PSScriptRoot 'generated/donor.swf'}
        & $Java '-Xmx1400m' '-jar' $sceneFfdec '-format' 'script:pcode' '-selectclass' 'fe.loc.Location,fe.inter.Camera,fe.loc.Game' `
            '-export' 'script' (Join-Path $PSScriptRoot ('generated/'+$sceneSourceSwf+'-pcode')) $sceneInput
        if($LASTEXITCODE -ne 0) {throw 'P-code export failed'}
    }
    & $Java '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' (Join-Path $PSScriptRoot 'generated/grafon-host.swf') (Join-Path $PSScriptRoot 'generated/host.xml')
    if($LASTEXITCODE -ne 0) {throw 'Host metadata export failed'}
    & $Python (Join-Path $PSScriptRoot 'pcode_plan.py')
    if($LASTEXITCODE -ne 0) {throw 'Method replacement planning failed'}
    & $Java '-Xmx1400m' '-jar' $sceneFfdec '-replace' (Join-Path $PSScriptRoot 'generated/grafon-host.swf') `
        (Join-Path $PSScriptRoot 'runtime/pfe.swf') (Join-Path $PSScriptRoot 'generated/audit/replace-args.txt')
    if($LASTEXITCODE -ne 0) {throw 'Method replacement failed'}
    if(-not(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'generated/original.xml'))) {
        & $Java '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' $BaseHost (Join-Path $PSScriptRoot 'generated/original.xml')
        if($LASTEXITCODE -ne 0) {throw 'Original metadata export failed'}
    }
    & $Java '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' (Join-Path $PSScriptRoot 'runtime/pfe.swf') (Join-Path $PSScriptRoot 'generated/final.xml')
    if($LASTEXITCODE -ne 0) {throw 'Final metadata export failed'}
    & $Python (Join-Path $PSScriptRoot 'pcode_plan.py') 'audit'
    if($LASTEXITCODE -ne 0) {throw 'Unrelated bytecode audit failed'}
}
$sceneAir = Join-Path $sceneTools 'airsdk/frameworks/libs/air/airglobal.swc'
$sceneSource = Join-Path $sceneMod 'src'
$sceneConfig = @"
<?xml version="1.0"?>
<flex-config xmlns="http://www.adobe.com/2006/flex-config">
  <target-player>32.0</target-player>
  <compiler><external-library-path><path-element>$sceneAir</path-element></external-library-path>
    <source-path><path-element>$sceneSource</path-element></source-path>
    <debug>false</debug><optimize>true</optimize>
  </compiler>
</flex-config>
"@
$sceneConfigPath = Join-Path $PSScriptRoot 'generated/compiler.xml'
[IO.File]::WriteAllText($sceneConfigPath,$sceneConfig,[Text.UTF8Encoding]::new($false))
foreach($sceneEntry in @('ContinuousSceneMod','ContinuousSceneProbe')) {
    if($ProbeOnly -and $sceneEntry -eq 'ContinuousSceneMod') {continue}
    $sceneFolder=if($sceneEntry -eq 'ContinuousSceneMod') {'ContinuousScene'} else {'ContinuousSceneProbe'}
    $sceneDocument=if($sceneEntry -eq 'ContinuousSceneMod') {'ContinuousSceneDoc.as'} else {'ContinuousSceneProbeDoc.as'}
    $sceneOutput=Join-Path $PSScriptRoot ('runtime/mods/'+$sceneFolder+'/release/'+$sceneEntry+'.swf')
    New-Item -ItemType Directory -Force -Path (Split-Path $sceneOutput) | Out-Null
& $Java '-Xmx512m' '-Dsun.io.useCanonCaches=false' '-Djava.util.Arrays.useLegacyMergeSort=true' `
    '-jar' (Join-Path $sceneFlex 'lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneFlex 'frameworks')) `
    ('-load-config='+$sceneConfigPath) '-swf-version=32' '-use-network=false' '-static-link-runtime-shared-libraries=true' `
    ('-output='+$sceneOutput) (Join-Path $sceneSource $sceneDocument)
if ($LASTEXITCODE -ne 0) { throw 'Driver compile failed' }
}
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'runtime/pfe.swf'),(Join-Path $PSScriptRoot 'runtime/mods/ContinuousScene/release/ContinuousSceneMod.swf') -Algorithm SHA256
