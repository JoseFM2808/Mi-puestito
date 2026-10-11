<#
.SYNOPSIS
  Arranca Mi Puestito en Staging con el Asistente de IA (NVIDIA NIM).

.DESCRIPTION
  1. Pide la API Key de NVIDIA de forma oculta. La llave vive SOLO en la memoria
     de esta ventana: no se escribe en el repo, ni en Drive, ni en archivos.
  2. Verifica qué modelos responden con esa llave y guarda el orden (solo nombres
     y tiempos) en la carpeta de datos de Staging.
  3. Opcional: guarda la llave en tu usuario de Windows (variable de entorno de
     usuario, en el registro) para no pegarla la próxima vez.
  4. Arranca el servidor en http://127.0.0.1:<Puerto>. Para cerrarlo: Ctrl+C.

  Los datos de Staging van a %LOCALAPPDATA%\MiPuestito-staging, separados de los
  datos reales (%LOCALAPPDATA%\MiPuestito). Usa el proyecto "demo" (PIN 0000).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\staging-con-ia.ps1
#>
param(
    [string]$Backend = (Join-Path $PSScriptRoot '..\backend'),
    [string]$Python = '',
    [int]$Puerto = 8765,
    [string]$Datos = (Join-Path $env:LOCALAPPDATA 'MiPuestito-staging')
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
$Host.UI.RawUI.WindowTitle = 'Mi Puestito · Staging con IA'

if (-not $Python) {
    $venv = Join-Path $Backend '..\.venv\Scripts\python.exe'
    $Python = if (Test-Path $venv) { $venv } else { 'py' }
}
$Backend = (Resolve-Path $Backend).Path

Write-Host ''
Write-Host '  Mi Puestito · Staging con Asistente de IA (NVIDIA)' -ForegroundColor Green
Write-Host '  -------------------------------------------------'
Write-Host "  Backend : $Backend"
Write-Host "  Datos   : $Datos  (separados de los reales)"
Write-Host ''

# ---- 1. La llave: oculta, solo en esta ventana --------------------------------
$llave = $null
$guardada = [Environment]::GetEnvironmentVariable('NVIDIA_API_KEY', 'User')
if ($guardada) {
    $usar = Read-Host '  Hay una llave de NVIDIA guardada en tu usuario de Windows. ¿Usarla? (S/N)'
    if ($usar -match '^[sS]') { $llave = $guardada }
}
if (-not $llave) {
    $segura = Read-Host '  Pega tu API Key de NVIDIA (no se mostrará) y presiona Enter' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)
    try { $llave = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}
$llave = "$llave".Trim()
if (-not $llave) { Write-Host '  No se ingresó ninguna llave. Cerrando.' -ForegroundColor Red; exit 1 }
if (-not $llave.StartsWith('nvapi-')) {
    Write-Host '  Aviso: las llaves de NVIDIA suelen empezar con "nvapi-". Se probará igual.' -ForegroundColor Yellow
}

$env:NVIDIA_API_KEY = $llave            # solo el proceso de esta ventana
$env:MI_PUESTITO_IA_PROVEEDOR = 'nvidia'
$env:MI_PUESTITO_DATOS = $Datos
$env:MI_PUESTITO_ENTORNO = 'local'
# Staging: registra intercambios SOLO del proyecto demo, seudonimizados (ADR-038)
$env:MI_PUESTITO_IA_REGISTRO = 'demo'
New-Item -ItemType Directory -Force $Datos | Out-Null

# ---- 2. Qué modelos responden con esta llave ----------------------------------
Push-Location $Backend
try {
    & $Python -m ia.verificar
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  Ningún modelo respondió. Revisa la llave en build.nvidia.com y vuelve a intentar.' -ForegroundColor Red
        Read-Host '  Presiona Enter para cerrar'
        exit 1
    }

    # ---- 3. ¿Guardar la llave para la próxima vez? ----------------------------
    if ($llave -ne $guardada) {
        $guardar = Read-Host '  ¿Guardar la llave en tu usuario de Windows para no pegarla otra vez? (S/N)'
        if ($guardar -match '^[sS]') {
            [Environment]::SetEnvironmentVariable('NVIDIA_API_KEY', $llave, 'User')
            Write-Host '  Guardada como variable de entorno de tu usuario (no en archivos).' -ForegroundColor Green
        }
    }
    $llave = $null

    # ---- 4. Servidor ------------------------------------------------------------
    Write-Host ''
    Write-Host "  Abriendo Mi Puestito en http://127.0.0.1:$Puerto  (cuenta Demo, PIN 0000)" -ForegroundColor Green
    Write-Host '  Para cerrar el servidor: Ctrl+C'
    Write-Host ''
    & $Python -m uvicorn main:app --host 127.0.0.1 --port $Puerto
}
finally {
    Pop-Location
}
