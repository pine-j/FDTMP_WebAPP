# How to Add Miniforge3 Python to System PATH Permanently

This guide shows you how to add Miniforge3 Python paths to your system PATH environment variable so that `python` and `py` commands work from any command prompt.

## Paths to Add

Add these three paths to your system PATH:
1. `C:\Users\AJITHA\AppData\Local\miniforge3`
2. `C:\Users\AJITHA\AppData\Local\miniforge3\Scripts`
3. `C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin`

---

## Method 1: Using Windows GUI (Recommended)

1. **Open System Properties:**
   - Press `Win + R` to open Run dialog
   - Type `sysdm.cpl` and press Enter
   - OR Right-click "This PC" → Properties → Advanced system settings

2. **Access Environment Variables:**
   - Click the "Environment Variables..." button (bottom right)

3. **Edit PATH:**
   - Under "System variables" (or "User variables" if you only want it for your user), find and select "Path"
   - Click "Edit..."

4. **Add the Paths:**
   - Click "New" and add each path:
     - `C:\Users\AJITHA\AppData\Local\miniforge3`
     - `C:\Users\AJITHA\AppData\Local\miniforge3\Scripts`
     - `C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin`
   - Click "OK" on each dialog

5. **Restart Terminal:**
   - Close and reopen your PowerShell/Command Prompt
   - Test with: `python --version`

---

## Method 2: Using PowerShell (Run as Administrator)

1. **Open PowerShell as Administrator:**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Run these commands:**

```powershell
# Add to User PATH (recommended - no admin needed)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Users\AJITHA\AppData\Local\miniforge3;C:\Users\AJITHA\AppData\Local\miniforge3\Scripts;C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin",
    "User"
)

# OR Add to System PATH (requires admin)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "Machine") + ";C:\Users\AJITHA\AppData\Local\miniforge3;C:\Users\AJITHA\AppData\Local\miniforge3\Scripts;C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin",
    "Machine"
)
```

3. **Restart Terminal:**
   - Close and reopen your terminal
   - Test with: `python --version`

---

## Method 3: Using Command Prompt (Run as Administrator)

1. **Open Command Prompt as Administrator:**
   - Press `Win + X`
   - Select "Command Prompt (Admin)" or "Terminal (Admin)"

2. **Run these commands:**

```cmd
setx PATH "%PATH%;C:\Users\AJITHA\AppData\Local\miniforge3;C:\Users\AJITHA\AppData\Local\miniforge3\Scripts;C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin" /M
```

Note: `/M` flag requires admin rights and adds to system PATH. Remove `/M` to add to user PATH only.

3. **Restart Terminal:**
   - Close and reopen your terminal
   - Test with: `python --version`

---

## Verify It Works

After adding to PATH and restarting your terminal, verify with:

```powershell
python --version
python -m pip --version
conda --version
```

You should see version information for each command.

---

## Troubleshooting

- **If `python` still doesn't work:** Make sure you closed and reopened your terminal completely
- **If paths already exist:** Windows will ignore duplicates, so it's safe to add them again
- **To check current PATH:** Run `echo $env:Path` in PowerShell or `echo %PATH%` in CMD
- **To remove paths later:** Use the same GUI method and delete the entries, or use PowerShell/CMD to edit PATH

---

## Quick PowerShell Script (One-time Setup)

You can also run this single PowerShell command (as Administrator for system PATH, or without admin for user PATH):

```powershell
$pathsToAdd = @(
    "C:\Users\AJITHA\AppData\Local\miniforge3",
    "C:\Users\AJITHA\AppData\Local\miniforge3\Scripts",
    "C:\Users\AJITHA\AppData\Local\miniforge3\Library\bin"
)
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
$newPath = $currentPath
foreach ($path in $pathsToAdd) {
    if ($newPath -notlike "*$path*") {
        $newPath += ";$path"
    }
}
[Environment]::SetEnvironmentVariable("Path", $newPath, "User")
Write-Host "PATH updated! Please restart your terminal."
```

