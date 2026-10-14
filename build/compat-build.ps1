param([switch]$VisionOnly)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneTools=Join-Path $sceneRoot 'mods/Sandevistan/build/tools'
$sceneJava='D:/Program Files/Adobe Animate 2024/jre/bin/java.exe'
$scenePython='C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $scenePython (Join-Path $PSScriptRoot 'compat_prepare.py')
if($LASTEXITCODE -ne 0) {throw 'Compatibility source preparation failed'}
$sceneConfig=Join-Path $PSScriptRoot 'generated/compat-compiler.xml'
$sceneStubs=Join-Path $sceneRoot 'mods/RealisticVision/build/GameStubs.swc'
$sceneAir=Join-Path $sceneTools 'airsdk/frameworks/libs/air/airglobal.swc'
$sceneSource=Join-Path $PSScriptRoot 'generated/rv-production'
@"
<flex-config><compiler><external-library-path><path-element>$sceneAir</path-element><path-element>$sceneStubs</path-element></external-library-path><source-path><path-element>$sceneSource</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/></compiler><target-player>32.0</target-player><swf-version>32</swf-version><use-network>false</use-network><static-link-runtime-shared-libraries>true</static-link-runtime-shared-libraries></flex-config>
"@ | Set-Content -LiteralPath $sceneConfig -Encoding UTF8
& $sceneJava '-Dfile.encoding=UTF-8' '-jar' (Join-Path $sceneTools 'flexsdk/lib/mxmlc.jar') ('+flexlib='+(Join-Path $sceneTools 'flexsdk/frameworks')) ('-load-config='+$sceneConfig) ('-output='+(Join-Path $PSScriptRoot 'runtime/mods/RealisticVision/release/RealisticVisionMod.swf')) (Join-Path $sceneSource 'RealisticVisionMod.as')
if($LASTEXITCODE -ne 0) {throw 'Vision compilation failed'}
if(-not $VisionOnly) {
    & (Join-Path $sceneRoot 'mods/WallBlend/build/build.ps1') -ToolRoot $sceneTools -Java $sceneJava -OutputDirectory (Join-Path $PSScriptRoot 'runtime/mods/WallBlend/release')
    if($LASTEXITCODE -ne 0) {throw 'Wall compilation failed'}
}
