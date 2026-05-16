$url = 'https://github.com/GyanD/codexffmpeg/releases/download/8.1.1/ffmpeg-8.1.1-full_build.zip'
$zip = "$env:TEMP\ffmpeg.zip"
$dest = "$env:LOCALAPPDATA\ffmpeg"
Write-Host "Downloading ffmpeg from $url ..."
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
Write-Host "Extracting to $dest ..."
Expand-Archive -Path $zip -DestinationPath $dest -Force
Remove-Item $zip
$binPath = Get-ChildItem -Path $dest -Directory | Select-Object -First 1
Write-Host ""
Write-Host "============================================"
Write-Host "ffmpeg installed to: $($binPath.FullName)\bin"
Write-Host ""
Write-Host "Now add this to your PATH (run in admin PowerShell):"
Write-Host "  [Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$($binPath.FullName)\bin', 'User')"
Write-Host "============================================"
