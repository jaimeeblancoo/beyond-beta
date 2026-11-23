param(
    [ValidateSet('download','prepare','analyze','report','all','verify-artifacts')][string]$Command='analyze',
    [string]$Config='config/analysis.toml',
    [switch]$SkipPdf,
    [string]$Python=''
)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    $projectPython=if($Python){$Python}else{Join-Path $projectRoot '.venv/Scripts/python.exe'}
    if (-not (Test-Path -LiteralPath $projectPython)) {throw 'Crea el entorno siguiendo README.md o indica -Python con la ruta de su ejecutable.'}
    $cliArguments=@('--project-root',$projectRoot,'--config',$Config,$Command)
    if($SkipPdf){$cliArguments+='--skip-pdf'}
    & $projectPython -m beyond_beta.cli @cliArguments
    if ($LASTEXITCODE -ne 0) {throw "Falló el comando $Command"}
} finally {Pop-Location}
