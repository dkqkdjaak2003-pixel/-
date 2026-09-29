# GstarCAD MCP 설치 스크립트 (Windows PowerShell)
# 사용: 저장소 루트에서  .\cad-mcp\setup.ps1  실행
$ErrorActionPreference = "Stop"
$Target = "C:\cad-mcp"

if (-not (Test-Path $Target)) {
    git clone https://github.com/daobataotie/CAD-MCP.git $Target
}

# GstarCAD용 설정으로 교체 (cad.type = "GCAD")
Copy-Item -Force "$PSScriptRoot\config.json" "$Target\src\config.json"

python -m pip install -e $Target

# Claude Code에 MCP 서버 등록 (사용자 전체 범위)
claude mcp add --scope user gstarcad -- python "$Target\src\server.py"

Write-Host "완료: GstarCAD를 실행한 뒤 Claude Code에서 /mcp 로 'gstarcad' 연결 상태를 확인하세요."
