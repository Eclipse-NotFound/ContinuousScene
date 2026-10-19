# Build into a separate candidate directory; an ongoing runtime test is untouched.
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$sceneFfdec=Join-Path $sceneRoot 'mods/Sandevistan/build/tools/ffdec/ffdec-cli.jar'
$sceneInput=Join-Path $PSScriptRoot 'candidate-v08-final/pfe.swf'
if((Get-FileHash -LiteralPath $sceneInput).Hash -ne 'A61EA4A30F0E4978173F2B92B5F33A02960098D706B810FC6196105278EFA73F'){throw 'Impact experiment requires the audited v08 candidate'}
$sceneOutput=Join-Path $PSScriptRoot 'candidate-v08-impact'
New-Item -ItemType Directory -Force -Path $sceneOutput|Out-Null
& $scenePython (Join-Path $PSScriptRoot 'prepare.py') (Join-Path $sceneRoot 'pfe_before_ContinuousScene_20261014-181702.swf') '--sources-only'
if($LASTEXITCODE -ne 0){throw 'Impact source preparation failed'}
$sceneSource=Join-Path $PSScriptRoot 'generated/v08-impact-renderer/fe/graph'
New-Item -ItemType Directory -Force -Path $sceneSource|Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/scripts/fe/graph/Grafon.as') -Destination (Join-Path $sceneSource 'Grafon.as') -Force
& $scenePython (Join-Path $PSScriptRoot 'decal_compact_experiment.py') (Join-Path $sceneSource 'Grafon.as')
if($LASTEXITCODE -ne 0){throw 'Explicit compact impact experiment failed'}
& $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-importScript' $sceneInput (Join-Path $sceneOutput 'pfe.swf') (Join-Path $PSScriptRoot 'generated/v08-impact-renderer')
if($LASTEXITCODE -ne 0){throw 'Impact renderer compilation failed'}
& $sceneJava '-Xmx1400m' '-jar' $sceneFfdec '-swf2xml' (Join-Path $sceneOutput 'pfe.swf') (Join-Path $sceneOutput 'pfe.xml')
if($LASTEXITCODE -ne 0){throw 'Impact metadata export failed'}
& $scenePython (Join-Path $PSScriptRoot 'renderer-audit.py') (Join-Path $sceneOutput 'pfe.swf') (Join-Path $PSScriptRoot 'cache/v08-baseline') (Join-Path $PSScriptRoot 'generated/v08-objects/methods.json')
if($LASTEXITCODE -ne 0){throw 'Unrelated native code audit failed'}
