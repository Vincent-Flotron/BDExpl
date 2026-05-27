# Define the regex pattern for version (Major.Minor.Patch.Build)
$pattern = '(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?'

# Read current version
try {
    $versionContent = Get-Content version.py -Raw
    if ($versionContent -notmatch $pattern) {
        Write-Error "Could not find valid version string matching '$pattern' in version.py"
        exit 1
    }
    $currentVersion = $matches[0]
    Write-Host "Current version found: $currentVersion"
}
catch {
    Write-Error "Failed to read version.py: $_"
    exit 1
}

$major = [int]$matches[1]
$minor = [int]$matches[2]
$patch = [int]$matches[3]
$build = if ($matches[4]) { [int]$matches[4] } else { 0 }

$minor += 1
$patch = 0
$build = 0
$newVersion = "$major.$minor.$patch.$build"

# Update version.py
$newContent = "VERSION='$newVersion'"
Set-Content version.py $newContent -NoNewline

# Display new version
Write-Host "`nPrevious version     : $currentVersion"
Write-Host "New compiled version : $newVersion"

# Create version info file for PyInstaller (using simpler format)
$versionInfoContent = @"
# UTF-8
#
# For more details about fixed file info:
# https://docs.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($major, $minor, $patch, $build),
    prodvers=($major, $minor, $patch, $build),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'FileDescription', u'DBExplorer'),
        StringStruct(u'InternalName', u'DBExpl'),
        StringStruct(u'LegalCopyright', u'https://github.com/Vincent-Flotron/BDExpl'),
        StringStruct(u'OriginalFilename', u'DBExpl.exe'),
        StringStruct(u'ProductName', u'DBExpl'),
        StringStruct(u'ProductVersion', u'$newVersion'),
        StringStruct(u'FileVersion', u'$newVersion')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@


Set-Content -Path "version_info.txt" -Value $versionInfoContent -Encoding UTF8

# Create executable with version info
Write-Host "Building executable..."
pyinstaller --onefile --windowed --hidden-import=win32timezone --collect-all cryptography --version-file=version_info.txt DBExpl.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!"
    Write-Host "Check DBExpl.exe properties for version and author info (in Comments field)"
}
else {
    Write-Error "Build failed with exit code $LASTEXITCODE"
}