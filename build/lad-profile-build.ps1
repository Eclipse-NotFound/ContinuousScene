# Diagnostic only; output never enters the runtime until explicitly selected.
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$java='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$python='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python (Join-Path $PSScriptRoot 'lad-profile.py')
if($LASTEXITCODE -ne 0){throw 'LAD timing source failed'}
$source=Join-Path $PSScriptRoot 'generated/lad-profile-source'
$out=Join-Path $PSScriptRoot 'candidate-lad-profile'
New-Item -ItemType Directory -Force -Path $out|Out-Null
$tools=Join-Path $root 'mods/Sandevistan/build/tools'
$air=Join-Path $tools 'airsdk/frameworks/libs/air/airglobal.swc'
$stub=Join-Path $root 'mods/LightAndDarkness/build/out/host-signatures.swc'
$config=Join-Path $out 'compile.xml'
$xml='<flex-config xmlns="http://www.adobe.com/2006/flex-config"><target-player>32.0</target-player><compiler><source-path><path-element>'+[Security.SecurityElement]::Escape($source)+'</path-element></source-path><external-library-path><path-element>'+[Security.SecurityElement]::Escape($air)+'</path-element><path-element>'+[Security.SecurityElement]::Escape($stub)+'</path-element></external-library-path><debug>false</debug><optimize>true</optimize></compiler></flex-config>'
[IO.File]::WriteAllText($config,$xml,[Text.UTF8Encoding]::new($false))
& $java '-Xmx512m' '-Dsun.io.useCanonCaches=false' '-Djava.util.Arrays.useLegacyMergeSort=true' '-jar' (Join-Path $tools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $tools 'flexsdk/frameworks')) ('-load-config='+$config) '-swf-version=32' '-use-network=false' '-static-link-runtime-shared-libraries=true' '-includes=lad.native.LadLampTarget' ('-output='+(Join-Path $out 'LightAndDarknessMod.swf')) (Join-Path $source 'LightAndDarknessDoc.as')
if($LASTEXITCODE -ne 0){throw 'LAD timing build failed'}
Get-FileHash (Join-Path $out 'LightAndDarknessMod.swf')
