# GstarCAD MCP 연결

오픈소스 MCP 서버 [daobataotie/CAD-MCP](https://github.com/daobataotie/CAD-MCP) (MIT 라이선스)를 사용해
Claude에서 GstarCAD(浩辰CAD)를 조작합니다. 이 서버는 AutoCAD / GstarCAD / ZWCAD를 지원하며,
Windows COM 인터페이스(pywin32)로 CAD를 제어합니다.

## 요구 사항

- Windows + GstarCAD 설치 (COM 자동화 지원 버전)
- Python 3.10 이상, Git
- Claude Code 또는 Claude Desktop (PC에서 실행)

> 클라우드(claude.ai/code) 세션은 Linux 컨테이너라서 PC의 GstarCAD에 접근할 수 없습니다.
> GstarCAD가 설치된 Windows PC에서 연결해야 합니다.

## 설치 (자동, Claude Code)

PowerShell에서 이 저장소 루트로 이동 후:

```powershell
.\cad-mcp\setup.ps1
```

스크립트가 하는 일:
1. `C:\cad-mcp`에 CAD-MCP 클론
2. `config.json`을 GstarCAD용(`"cad": {"type": "GCAD"}`)으로 교체
3. `pip install -e C:\cad-mcp`
4. `claude mcp add --scope user gstarcad -- python "C:\cad-mcp\src\server.py"`

## 설치 (수동, Claude Desktop)

1~3단계는 위와 같이 진행한 뒤 `%APPDATA%\Claude\claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "gstarcad": {
      "command": "python",
      "args": ["C:\\cad-mcp\\src\\server.py"]
    }
  }
}
```

## 확인

1. GstarCAD 실행 (실행 중이 아니면 서버가 COM으로 새로 띄우고 `startup_wait_time` 20초 대기)
2. Claude Code에서 `/mcp` → `gstarcad`가 connected인지 확인
3. 예: "원점에 반지름 50인 원을 그리고 레이어 목록 보여줘"

## 참고

- 서버는 COM ProgID `GCAD.Application` → `GstarCAD.Application` 순서로 연결을 시도합니다
  (버전에 따라 등록 이름이 다름, 원본 `src/cad_controller.py`).
- 제공 도구: 선/원/호/타원/폴리라인/사각형/문자/해치/치수 그리기, 레이어·객체 조회, 스크린샷,
  지우기/이동/회전/축척/복사/대칭/오프셋/배열, 실행 취소, 레이어 관리, 도면 새로 만들기/열기/저장, 블록, 명령어 직접 실행.
