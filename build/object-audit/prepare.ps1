param([switch]$CompileOnly,[switch]$Candidate)
$ErrorActionPreference='Stop'
$objectMod=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$objectRoot=(Resolve-Path -LiteralPath (Join-Path $objectMod '../..')).Path
$objectOut=Join-Path $objectMod 'build/generated/object-audit-20261019'
$objectRuntime=Join-Path $objectOut 'runtime'
$objectTools=Join-Path $objectRoot 'mods/Sandevistan/build/tools'
$objectJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
New-Item -ItemType Directory -Force -Path $objectRuntime | Out-Null
$objectCompileLock=[IO.File]::Open((Join-Path $objectRuntime 'objects.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
if(-not $CompileOnly -and -not $Candidate) {
    if(Test-Path -LiteralPath (Join-Path $objectOut 'baseline-hashes.json')) {throw 'Baseline already frozen; use CompileOnly or Candidate'}
    foreach($objectPattern in @('texture*.swf','sprite*.swf','sound*.swf','text_*.xml','lang.xml','pfe.swf')) {
        Get-ChildItem -LiteralPath $objectRoot -Filter $objectPattern -File | Copy-Item -Destination $objectRuntime
    }
    foreach($objectFolder in @('Rooms','Music','Texture')) {
        $objectPath=Join-Path $objectRoot $objectFolder
        if(Test-Path -LiteralPath $objectPath){Copy-Item -LiteralPath $objectPath -Destination $objectRuntime -Recurse}
    }
    $objectManifest=Get-Content -LiteralPath (Join-Path $objectRoot 'mods/loader-manifest.txt') -Encoding UTF8
    $objectLines=@($objectManifest | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'})
    $objectHashes=@()
    foreach($objectLine in $objectLines) {
        $objectFields=$objectLine.Split('|')
        $objectSource=Join-Path $objectRoot ('mods/'+$objectFields[0])
        $objectTarget=Join-Path $objectRuntime ('mods/'+$objectFields[0])
        New-Item -ItemType Directory -Force -Path $objectTarget | Out-Null
        foreach($objectFolder in @('release','config')) {
            if(Test-Path -LiteralPath (Join-Path $objectSource $objectFolder)){Copy-Item -LiteralPath (Join-Path $objectSource $objectFolder) -Destination $objectTarget -Recurse}
        }
        if($objectFields[0] -eq 'LightAndDarkness'){Copy-Item -LiteralPath (Join-Path $objectSource 'atmosphere.json') -Destination $objectTarget}
        $objectHashes+=Get-FileHash -LiteralPath (Join-Path $objectTarget ('release/'+$objectFields[1]+'.swf'))
    }
    $objectHashes+=Get-FileHash -LiteralPath (Join-Path $objectRuntime 'pfe.swf')
    $objectHashes|Select-Object Path,Hash|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $objectOut 'baseline-hashes.json')
    Copy-Item -LiteralPath (Join-Path $objectRuntime 'mods/ContinuousScene/release/ContinuousSceneMod.swf') -Destination (Join-Path $objectOut 'baseline-ContinuousSceneMod.swf')
    $objectLines+='ContinuousSceneObjectProbe|ContinuousSceneObjectProbe|1|0|0'
    [IO.File]::WriteAllLines((Join-Path $objectRuntime 'mods/loader-manifest.txt'),$objectLines,[Text.UTF8Encoding]::new($false))
    $objectDescriptor=@'
<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
 <id>pfe-modsettings-continuous-objects-01a151d4</id><versionNumber>0.1.0</versionNumber>
 <filename>ContinuousSceneObjectAudit</filename><name>Remains Object Audit</name>
 <initialWindow><content>pfe.swf</content><visible>false</visible><width>1280</width><height>800</height><renderMode>direct</renderMode><resizable>true</resizable></initialWindow>
 <supportedProfiles>extendedDesktop</supportedProfiles>
</application>
'@
    [IO.File]::WriteAllText((Join-Path $objectRuntime 'application.xml'),$objectDescriptor,[Text.UTF8Encoding]::new($false))
}
$objectSource=Join-Path $PSScriptRoot 'src'
$objectExtra=Join-Path $objectMod 'src'
$objectDoc='ContinuousSceneObjectProbeDoc.as'
$objectOutput=Join-Path $objectRuntime 'mods/ContinuousSceneObjectProbe/release/ContinuousSceneObjectProbe.swf'
if($Candidate) {
    $objectSource=Join-Path $objectOut ('candidate-src-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $objectSource | Out-Null
    foreach($objectName in @('ContinuousSceneDoc.as','ContinuousSceneMod.as','NativeSceneAdapter.as')) {
        Copy-Item -LiteralPath (Join-Path $objectExtra $objectName) -Destination $objectSource
    }
    $objectExtra=$objectSource
    $objectDoc='ContinuousSceneDoc.as'
    $objectOutput=Join-Path $objectOut 'candidate-ContinuousSceneMod.swf'
    Get-ChildItem -LiteralPath $objectSource -File|Get-FileHash|Select-Object Path,Hash|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $objectSource 'hashes.json')
}
$objectAir=Join-Path $objectTools 'airsdk/frameworks/libs/air/airglobal.swc'
$objectConfig=@"
<?xml version="1.0"?>
<flex-config xmlns="http://www.adobe.com/2006/flex-config">
 <target-player>32.0</target-player>
 <compiler><external-library-path><path-element>$objectAir</path-element></external-library-path>
 <source-path><path-element>$objectSource</path-element><path-element>$objectExtra</path-element></source-path>
 <debug>false</debug><optimize>true</optimize></compiler>
</flex-config>
"@
$objectConfigPath=Join-Path $objectOut 'compiler.xml'
[IO.File]::WriteAllText($objectConfigPath,$objectConfig,[Text.UTF8Encoding]::new($false))
New-Item -ItemType Directory -Force -Path (Split-Path $objectOutput) | Out-Null
& $objectJava '-Xmx512m' '-Dsun.io.useCanonCaches=false' '-Djava.util.Arrays.useLegacyMergeSort=true' '-jar' (Join-Path $objectTools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $objectTools 'flexsdk/frameworks')) ('-load-config='+$objectConfigPath) '-swf-version=32' '-use-network=false' '-static-link-runtime-shared-libraries=true' ('-output='+$objectOutput) (Join-Path $objectSource $objectDoc)
if($LASTEXITCODE -ne 0){throw 'Object audit compile failed'}
Get-FileHash -LiteralPath $objectOutput
} finally {$objectCompileLock.Dispose()}
