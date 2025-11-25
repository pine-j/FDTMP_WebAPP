Run this PowerShell command to move Miniforge paths to the top of your user PATH environment variable:

```powershell
$miniforgePaths = @(
    "C:\Users\AJITHA\AppData\Local\miniforge3",
    "C:\Users\AJITHA\AppData\Local\miniforge3\Scripts",
    "C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin"
)

# Get current User PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathParts = $currentPath -split ";"

# Filter out Miniforge paths from current list to avoid duplicates
$cleanPathParts = $pathParts | Where-Object { $miniforgePaths -notcontains $_ }

# Combine: Miniforge Paths + Cleaned Old Paths
$newPathParts = $miniforgePaths + $cleanPathParts
$newPath = $newPathParts -join ";"

# Set the new User PATH
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")

Write-Host "Success! Miniforge paths moved to the top."
Write-Host "Please RESTART your terminal/Cursor for this to take effect."
```



