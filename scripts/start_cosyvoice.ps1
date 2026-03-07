$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$cosyRoot = Join-Path $projectRoot "third_party\\CosyVoice"
$cosyPy = Join-Path $cosyRoot ".venv\\Scripts\\python.exe"
$cosyScript = Join-Path $cosyRoot "runtime\\python\\fastapi\\server.py"
$cacheDir = Join-Path $projectRoot "third_party\\models\\modelscope_cache"

if (-not (Test-Path $cosyPy)) {
  throw "CosyVoice venv python not found: $cosyPy"
}
if (-not (Test-Path $cosyScript)) {
  throw "CosyVoice server script not found: $cosyScript"
}

$env:MODELSCOPE_CACHE = $cacheDir

$port = 50000
$modelDir = "iic/CosyVoice2-0.5B"

& $cosyPy $cosyScript --port $port --model_dir $modelDir
