# check_system.ps1
# Diagnostico COMPLETO da maquina para o projeto Identificador de Animais.
# Cobre: CPU, RAM, discos (com benchmark de leitura real), GPU, motherboard, page file.
# Uso: powershell -ExecutionPolicy Bypass -File .\check_system.ps1
# Saida: system_report.txt no mesmo diretorio.

$ErrorActionPreference = "Continue"
$out = Join-Path $PSScriptRoot "system_report.txt"

function W { param([string]$msg) $msg | Add-Content $out; Write-Host $msg }
function Section($title) { W ""; W ("=" * 70); W $title; W ("=" * 70) }

"=== Diagnostico de sistema - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Set-Content $out
Write-Host "=== Diagnostico de sistema (vai gravar em $out) ==="

# =====================================================================
Section "1. SISTEMA OPERACIONAL"
# =====================================================================
$os = Get-CimInstance Win32_OperatingSystem
W ("OS: {0} {1} (build {2})" -f $os.Caption, $os.OSArchitecture, $os.BuildNumber)
W ("Hostname: {0}" -f $env:COMPUTERNAME)
W ("Uptime: {0:N1} horas" -f ((Get-Date) - $os.LastBootUpTime).TotalHours)

# =====================================================================
Section "2. CPU"
# =====================================================================
$cpu = Get-CimInstance Win32_Processor
foreach ($c in $cpu) {
    W ("Modelo:         {0}" -f $c.Name.Trim())
    W ("Cores fisicos:  {0}" -f $c.NumberOfCores)
    W ("Threads:        {0}" -f $c.NumberOfLogicalProcessors)
    W ("Clock max:      {0} MHz" -f $c.MaxClockSpeed)
    W ("Socket:         {0}" -f $c.SocketDesignation)
    W ("L3 cache:       {0} KB" -f $c.L3CacheSize)
}

# Carga atual da CPU (amostra de 2s)
try {
    $load = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 2 -ErrorAction Stop).CounterSamples |
            Select-Object -ExpandProperty CookedValue | Measure-Object -Average
    W ("Carga atual:    {0:N1}%" -f $load.Average)
} catch {
    W "Carga atual:    [nao foi possivel medir]"
}

# =====================================================================
Section "3. RAM"
# =====================================================================
$ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramFree  = [math]::Round($os.FreePhysicalMemory   / 1MB, 1)
$ramUsed  = $ramTotal - $ramFree
W ("Total:          {0} GB" -f $ramTotal)
W ("Em uso:         {0} GB" -f $ramUsed)
W ("Livre:          {0} GB" -f $ramFree)

W ""
W "Pentes instalados:"
$sticks = Get-CimInstance Win32_PhysicalMemory
$sticks | Format-Table -AutoSize `
    @{N='Slot';E={$_.DeviceLocator}},
    @{N='Size_GB';E={[math]::Round($_.Capacity/1GB,1)}},
    @{N='Speed_MHz';E={$_.ConfiguredClockSpeed}},
    @{N='Tipo';E={
        switch ($_.SMBIOSMemoryType) {
            20 {'DDR'}; 21 {'DDR2'}; 24 {'DDR3'}; 26 {'DDR4'}; 34 {'DDR5'}; default {"Tipo $($_.SMBIOSMemoryType)"}
        }
    }},
    @{N='Manufacturer';E={$_.Manufacturer}},
    @{N='PartNumber';E={$_.PartNumber}} |
    Out-String -Stream | ForEach-Object { if ($_.Trim()) { W $_ } }

W ("Numero de pentes: {0} (canais usados: vide BIOS)" -f $sticks.Count)

# =====================================================================
Section "4. MOTHERBOARD"
# =====================================================================
$mb = Get-CimInstance Win32_BaseBoard
$bios = Get-CimInstance Win32_BIOS
W ("Fabricante:     {0}" -f $mb.Manufacturer)
W ("Modelo:         {0}" -f $mb.Product)
W ("Versao:         {0}" -f $mb.Version)
W ("BIOS:           {0} {1} ({2})" -f $bios.Manufacturer, $bios.SMBIOSBIOSVersion, $bios.ReleaseDate)

# =====================================================================
Section "5. DISCOS FISICOS (tipo / barramento)"
# =====================================================================
Get-PhysicalDisk |
    Format-Table -AutoSize DeviceId, FriendlyName, MediaType, BusType,
        @{N='Size_GB'; E={[math]::Round($_.Size / 1GB, 1)}},
        HealthStatus,
        @{N='SpindleSpeed'; E={if($_.SpindleSpeed -eq 0){'-'}else{$_.SpindleSpeed}}} |
    Out-String -Stream | ForEach-Object { if ($_.Trim()) { W $_ } }

# =====================================================================
Section "6. VOLUMES (letras / espaco)"
# =====================================================================
Get-Volume | Where-Object DriveLetter | Sort-Object DriveLetter |
    Format-Table -AutoSize DriveLetter, FileSystemLabel,
        @{N='Size_GB'; E={[math]::Round($_.Size          / 1GB, 1)}},
        @{N='Free_GB'; E={[math]::Round($_.SizeRemaining / 1GB, 1)}},
        @{N='Free_%';  E={if($_.Size -gt 0){[math]::Round($_.SizeRemaining/$_.Size*100,1)}else{0}}},
        FileSystem, DriveType |
    Out-String -Stream | ForEach-Object { if ($_.Trim()) { W $_ } }

# =====================================================================
Section "7. BENCHMARK DE LEITURA SEQUENCIAL (arquivos reais, randomicos)"
# =====================================================================

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

    # Aquecimento descartado pra mitigar cache do SO
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

$tests = [ordered]@{
    "E:\datasets\coco\images\train2017"      = "COCO train     (C:)"
    "E:\datasets\coco\images\val2017"        = "COCO val       (C:)"
    "E:\datasets\br_detection\images\val"    = "BR detection val (C:)"
    "E:\datasets\br_detection\images\train"  = "BR detection   (C:)"
    "C:\Windows\System32"                    = "C:\Windows\Sys32"
    "C:\Users\alves"                         = "C:\Users\alves"
}

foreach ($path in $tests.Keys) {
    $label  = $tests[$path]
    $result = Test-ReadSpeed -Path $path
    W ("{0,-30} : {1}" -f $label, $result)
}

# =====================================================================
Section "8. GPU"
# =====================================================================
$gpus = Get-CimInstance Win32_VideoController
foreach ($g in $gpus) {
    W ("GPU:            {0}" -f $g.Name)
    W ("VRAM:           {0:N1} GB" -f ($g.AdapterRAM / 1GB))
    W ("Driver:         {0}" -f $g.DriverVersion)
}

# nvidia-smi pra info detalhada da NVIDIA
W ""
W "nvidia-smi:"
try {
    $nvidiaSmi = & nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu,driver_version,pcie.link.gen.current,pcie.link.width.current --format=csv 2>&1
    $nvidiaSmi | ForEach-Object { W $_ }
} catch {
    W "  [nvidia-smi nao disponivel ou GPU NVIDIA nao detectada]"
}

# =====================================================================
Section "9. PAGE FILE (memoria virtual)"
# =====================================================================
$pf = Get-CimInstance Win32_PageFileUsage
if ($pf) {
    foreach ($p in $pf) {
        W ("Arquivo:        {0}" -f $p.Name)
        W ("Tamanho atual:  {0} MB" -f $p.AllocatedBaseSize)
        W ("Em uso:         {0} MB" -f $p.CurrentUsage)
        W ("Pico:           {0} MB" -f $p.PeakUsage)
    }
} else {
    W "Page file: [gerenciado automaticamente pelo sistema ou nao detectado]"
}

# =====================================================================
Section "10. PLANO DE ENERGIA"
# =====================================================================
try {
    $plan = (powercfg /getactivescheme) -replace "GUID do plano de energia:|Power Scheme GUID:|.*\)\s*", ""
    W ("Ativo: {0}" -f $plan.Trim())
} catch {
    W "[nao foi possivel detectar]"
}

# =====================================================================
Section "11. CONTROLADORES NVMe / SATA (para verificar PCIe gen)"
# =====================================================================
$controllers = Get-PnpDevice -Class SCSIAdapter, SCSIController -ErrorAction SilentlyContinue |
               Where-Object Status -eq "OK"
foreach ($c in $controllers) {
    W ("- {0}" -f $c.FriendlyName)
}

W ""
W "=== Fim do diagnostico ==="
W ("Relatorio salvo em: $out")
Write-Host ""
Write-Host "Pronto. Compartilhe o conteudo de '$out' com o Cowork."
