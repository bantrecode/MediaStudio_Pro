# ==============================================================================
# All-in-One Media Studio Pro - Build Script (build.ps1)
# Quy trình tự động tuần tự:
# 1. Chạy Pytest toàn bộ test suite (chặn đứng nếu có test fail)
# 2. Đóng gói PyInstaller onedir (upx=False, nhúng Windows Version Resource)
# 3. Biên dịch Inno Setup tạo MediaStudio_Setup.exe (nếu có ISCC)
# 4. Tạo gói nén di động MediaStudio_Portable.zip
# 5. Xuất mã băm SHA256 cho các gói phân phối
# ==============================================================================

[CmdletBinding()]
param (
    [switch]$SkipTests,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ScriptDir

function Write-Header($text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " [BUILD] $text" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Find-Python {
    # 1. Kiểm tra Python trong AppData người dùng (tránh WindowsApps stub)
    $candidates = @(
        "$env:LOCALAPPDATA\Python\bin\python.exe",
        "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }

    # 2. Kiểm tra Python trong PATH (loại trừ WindowsApps)
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch "WindowsApps") { return $cmd.Source }

    return "python"
}

function Find-ISCC {
    $cmd = Get-Command ISCC -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$ScriptDir\tools\inno\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

$PythonExe = Find-Python
Write-Host "[*] Sử dụng Python: $PythonExe" -ForegroundColor Yellow

# ------------------------------------------------------------------------------
# BƯỚC 1: KIỂM THỬ TỰ ĐỘNG BẰNG PYTEST
# ------------------------------------------------------------------------------
if (-not $SkipTests) {
    Write-Header "BƯỚC 1/5: Chạy Pytest kiểm thử tự động..."
    $pytestArgs = @("-m", "pytest", "tests", "-v", "--tb=short")
    & $PythonExe @pytestArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[-] Pytest thất bại! Dừng quy trình build để đảm bảo chất lượng phần mềm."
        exit $LASTEXITCODE
    }
    Write-Host "[+] 100% Tests đã PASS thành công!" -ForegroundColor Green
} else {
    Write-Host "[!] Đã bỏ qua bước kiểm thử Pytest theo yêu cầu." -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# BƯỚC 2: ĐÓNG GÓI PYINSTALLER (ONEDIR, UPX=FALSE, VERSION INFO)
# ------------------------------------------------------------------------------
Write-Header "BƯỚC 2/5: Đóng gói PyInstaller (onedir, upx=False)..."

# Dọn dẹp dist cũ
$DistAppDir = Join-Path $ScriptDir "dist\MediaStudio"
if (Test-Path $DistAppDir) {
    Write-Host "[*] Dọn dẹp thư mục dist cũ: $DistAppDir"
    Remove-Item -Path $DistAppDir -Recurse -Force
}

$SpecFile = Join-Path $ScriptDir "build\app.spec"
if (-not (Test-Path $SpecFile)) {
    Write-Error "[-] Không tìm thấy file spec: $SpecFile"
    exit 1
}

$pyinstallerArgs = @("-m", "PyInstaller", $SpecFile, "--noconfirm", "--clean")
& $PythonExe @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "[-] PyInstaller build thất bại với mã lỗi $LASTEXITCODE"
    exit $LASTEXITCODE
}

$TargetExe = Join-Path $DistAppDir "MediaStudio.exe"
if (-not (Test-Path $TargetExe)) {
    Write-Error "[-] Không tìm thấy file thực thi đầu ra: $TargetExe"
    exit 1
}
Write-Host "[+] PyInstaller hoàn tất: $TargetExe" -ForegroundColor Green

# Dọn dẹp build/app cache
$BuildTemp = Join-Path $ScriptDir "build\app"
if (Test-Path $BuildTemp) {
    Remove-Item -Path $BuildTemp -Recurse -Force -ErrorAction SilentlyContinue
}

# ------------------------------------------------------------------------------
# BƯỚC 3: BIÊN DỊCH BỘ CÀI ĐẶT INNO SETUP (MediaStudio_Setup.exe)
# ------------------------------------------------------------------------------
Write-Header "BƯỚC 3/5: Biên dịch Installer bằng Inno Setup..."
$IsccExe = Find-ISCC
$SetupExe = Join-Path $ScriptDir "dist\MediaStudio_Setup.exe"

if ($IsccExe) {
    Write-Host "[*] Tìm thấy Inno Setup Compiler: $IsccExe" -ForegroundColor Green
    $IssFile = Join-Path $ScriptDir "installer\MediaStudio.iss"
    & "$IsccExe" "$IssFile"
    if ($LASTEXITCODE -eq 0 -and (Test-Path $SetupExe)) {
        Write-Host "[+] Đã tạo bộ cài đặt Inno Setup: $SetupExe" -ForegroundColor Green
    } else {
        Write-Warning "[!] Quá trình biên dịch Inno Setup gặp cảnh báo hoặc lỗi."
    }
} else {
    Write-Host "[!] Không tìm thấy ISCC.exe (Inno Setup 6 chưa được cài đặt)." -ForegroundColor Yellow
    Write-Host "    Để biên dịch MediaStudio_Setup.exe, hãy cài đặt Inno Setup 6 từ: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "    Hoặc chạy: winget install JRSoftware.InnoSetup" -ForegroundColor Yellow
}

# ------------------------------------------------------------------------------
# BƯỚC 4: TẠO GÓI NÉN DI ĐỘNG PORTABLE ZIP
# ------------------------------------------------------------------------------
$ZipFile = Join-Path $ScriptDir "dist\MediaStudio_Portable.zip"
if (-not $SkipZip) {
    Write-Header "BƯỚC 4/5: Tạo gói Portable ZIP (MediaStudio_Portable.zip)..."
    if (Test-Path $ZipFile) {
        Remove-Item -Path $ZipFile -Force
    }
    Write-Host "[*] Đang nén $DistAppDir -> $ZipFile..."
    try {
        Add-Type -AssemblyName "System.IO.Compression.FileSystem" -ErrorAction SilentlyContinue
        [System.IO.Compression.ZipFile]::CreateFromDirectory($DistAppDir, $ZipFile, [System.IO.Compression.CompressionLevel]::Optimal, $false)
    } catch {
        Compress-Archive -Path "$DistAppDir\*" -DestinationPath $ZipFile -CompressionLevel Optimal
    }
    if (Test-Path $ZipFile) {
        $zipSizeMb = [math]::Round((Get-Item $ZipFile).Length / 1MB, 2)
        Write-Host "[+] Đã tạo Portable ZIP thành công: $ZipFile ($zipSizeMb MB)" -ForegroundColor Green
    }
}

# ------------------------------------------------------------------------------
# BƯỚC 5: TÍNH TOÁN & XUẤT SHA256 CHECKSUMS
# ------------------------------------------------------------------------------
Write-Header "BƯỚC 5/5: Bảng mã băm SHA256 của các gói phát hành..."

$Artifacts = @()
if (Test-Path $TargetExe) { $Artifacts += $TargetExe }
if (Test-Path $SetupExe)  { $Artifacts += $SetupExe }
if (Test-Path $ZipFile)   { $Artifacts += $ZipFile }

$ChecksumOutput = @()
foreach ($file in $Artifacts) {
    $hash = Get-FileHash -Path $file -Algorithm SHA256
    $item = Get-Item $file
    $sizeMb = [math]::Round($item.Length / 1MB, 2)
    $ChecksumOutput += [PSCustomObject]@{
        FileName = $item.Name
        "Size(MB)" = $sizeMb
        SHA256 = $hash.Hash
    }
}

$ChecksumOutput | Format-Table -AutoSize

# Lưu danh sách SHA256 vào file text
$Sha256File = Join-Path $ScriptDir "dist\SHA256SUMS.txt"
$ChecksumOutput | ForEach-Object { "$($_.SHA256) *$($_.FileName)" } | Set-Content -Path $Sha256File -Encoding UTF8
Write-Host "[+] Đã lưu checksums vào: $Sha256File" -ForegroundColor Green

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [SUCCESS] QUY TRÌNH BUILD HOÀN TẤT THÀNH CÔNG!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
