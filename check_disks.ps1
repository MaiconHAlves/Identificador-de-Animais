# check_disks.ps1
# Diagnostico de discos + RAM para o projeto Identificador de Animais.
# Uso: powershell -ExecutionPolicy Bypass -File .\check_disks.ps1
# Saida: disk_report.txt no mesmo diretorio.

$ErrorActionPreference = "Continue"
$out = Join-Path $PSScriptRoot "disk_report.txt"

function W { param([string]$msg) $msg | Add-Content $out; Write-Host $msg }

"=== Diagnostico de discos + RAM - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content $out
Write-Host "=== Diagnostico de discos + RAM ==="

# --- RAM ---
W ""
W "--- RAM ---"
$os = Get-CimInstance Win32_OperatingSystem
$ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramFree  = [math]::Round($os.FreePhysicalMemory   / 1MB, 1)
W ("Total: {0} GB  |  Livre: {1} GB" -f $ramTotal, $ramFree)

# --- Discos fisicos (tipo: HDD / SSD / NVMe via BusType) ---
W ""
W "--- Discos fisicos (tipo / barramento) ---"
Get-PhysicalDisk |
    Format-Table -AutoSize DeviceId, FriendlyName, MediaType, BusType,
        @{N='Size_GB'; E={[math]::Round($_.Size / 1GB, 1)}}, HealthStatus |
    Out-String -Stream | ForEach-Object { if ($_.Trim()) { W $_ } }

# --- Volumes (letras / espaco) ---
W "--- Volumes ---"
Get-Volume | Where-Object DriveLetter | Sort-Object DriveLetter |
    Format-Table -AutoSize DriveLetter, FileSystemLabel,
        @{N='Size_GB'; E={[math]::Round($_.Size          / 1GB, 1)}},
        @{N='Free_GB'; E={[math]::Round($_.SizeRemaining / 1GB, 1)}},
        FileSystem, DriveType |
    Out-String -Stream | ForEach-Object { if ($_.Trim()) { W $_ } }

# --- Benchmark de leitura sequencial em arquivos reais ---
function Test-ReadSpeed {
    param(
        [string]$Path,
        [int]$MaxFiles = 400,
        [int]$TargetMB = 300
    )

    if (-not (Test-Path $Path)) { return "[caminho nao existe]" }

    $all = @(Get-ChildItem -Path $Path -Recurse -File -ErrorAction SilentlyContinue)
    if ($all.Count -eq 0) { return "[sem arquivos]" }

    $files = @($all | Get-Random -Count ([Math]::Min($MaxFiles, $all.Count)))

    # Aquecimento descartado (1o arquivo) pra mitigar efeito de cache do SO
    try { [void][System.IO.File]::ReadAllBytes($files[0].FullName) } catch {}

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $totalBytes = 0L
    $count = 0
    foreach ($f in ($files | Select-Object -Skip 1)) {
        try {
            $b = [System.IO.File]::ReadAllBytes($f.FullName)
            $totalBytes += $b.Length
            $count++
            if ($totalBytes -ge ($TargetMB * 1MB)) { break }
        } catch {}
    }
    $sw.Stop()

    $mb   = $totalBytes / 1MB
    $sec  = $sw.Elapsed.TotalSeconds
    $mbps = if ($sec -gt 0) { $mb / $sec } else { 0 }

    return ("{0,7:N1} MB em {1,5:N2}s = {2,7:N1} MB/s  ({3} arquivos)" -f $mb, $sec, $mbps, $count)
}

W ""
W "--- Velocidade de leitura sequencial (arquivos reais, randomicos) ---"

$tests = [ordered]@{
    "E:\datasets\coco\images\train2017"      = "COCO train      (C:)"
    "E:\datasets\coco\images\val2017"        = "COCO val        (C:)"
    "E:\datasets\br_detection\images\train"  = "BR detection    (C:)"
    "C:\Windows\System32"                    = "C:\Windows\Sys32 (C:)"
    "C:\Users\alves"                         = "C:\Users\alves   (C:)"
}

foreach ($path in $tests.Keys) {
    $label  = $tests[$path]
    $result = Test-ReadSpeed -Path $path
    W ("{0,-25} : {1}" -f $label, $result)
}

W ""
W "=== Fim do diagnostico ==="
W ("Relatorio salvo em: $out")
