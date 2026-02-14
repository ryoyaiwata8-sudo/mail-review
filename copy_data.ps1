$source = "C:\Users\ryoya\Documents\intern\vexum\トラベルスタンダード\電話*"
$dest = "c:\Users\ryoya\.gemini\antigravity\playground\thermal-coronal\data"
if (!(Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest
}
Copy-Item -Path $source -Destination $dest -Recurse -Force
Write-Host "Copy attempted from $source to $dest"
