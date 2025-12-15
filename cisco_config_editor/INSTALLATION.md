# 설치 및 실행 가이드

## 목차
1. [시스템 요구사항](#시스템-요구사항)
2. [설치 방법](#설치-방법)
3. [실행 방법](#실행-방법)
4. [문제 해결](#문제-해결)

## 시스템 요구사항

### 필수 사항
- **Python 3.8 이상**
- **운영체제**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **메모리**: 최소 2GB RAM (권장 4GB)
- **디스크 공간**: 500MB 이상

### 네트워크 (실시간 연결 기능 사용 시)
- Cisco 장비와 TCP/IP 연결 가능
- SSH (포트 22) 또는 Telnet (포트 23) 접근 권한

## 설치 방법

### 1. Python 설치 확인

터미널/명령 프롬프트에서 Python 버전 확인:

```bash
python --version
# 또는
python3 --version
```

3.8 이상이어야 합니다. 설치가 필요한 경우:
- Windows: https://www.python.org/downloads/
- macOS: `brew install python3`
- Linux: `sudo apt install python3 python3-pip`

### 2. 프로젝트 다운로드

**방법 A: Git을 사용하는 경우**
```bash
git clone https://github.com/yourusername/cisco-config-manager.git
cd cisco-config-manager
```

**방법 B: ZIP 파일 다운로드**
1. GitHub에서 "Code" → "Download ZIP" 클릭
2. 압축 해제
3. 터미널에서 압축 해제한 폴더로 이동

### 3. 가상환경 생성 (권장)

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

가상환경이 활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다.

### 4. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 5. 선택적 패키지 설치 (실시간 연결 기능)

SSH/Telnet 연결이 필요한 경우:

```bash
pip install netmiko paramiko textfsm
```

## 실행 방법

### 기본 실행

```bash
python main.py
```

### 문제 발생 시

**Python 3 명시적 실행:**
```bash
python3 main.py
```

**가상환경 활성화 확인:**
```bash
# 가상환경이 활성화되어 있어야 합니다
# 프롬프트에 (venv)가 표시되는지 확인
```

## 프로젝트 구조 확인

설치 후 다음과 같은 구조여야 합니다:

```
cisco-config-manager/
├── main.py                 # ✓ 실행 파일
├── requirements.txt        # ✓ 의존성 목록
├── README.md              # ✓ 문서
├── LICENSE                # ✓ 라이선스
├── .gitignore            # ✓ Git 제외 파일
│
├── ui/                   # ✓ UI 모듈
│   ├── __init__.py
│   ├── main_window.py
│   ├── device_manager_dialog.py
│   ├── dialogs.py
│   └── tabs/
│       ├── __init__.py
│       ├── global_tab.py
│       ├── interface_tab.py
│       ├── vlan_tab.py
│       ├── routing_tab.py
│       ├── switching_tab.py
│       ├── security_tab.py
│       ├── acl_tab.py
│       └── ha_tab.py
│
└── core/                 # ✓ 핵심 로직
    ├── __init__.py
    ├── cli_analyzer.py
    ├── device_manager.py
    ├── config_diff.py
    ├── connection_manager.py
    ├── templates.py
    └── validators.py
```

## 문제 해결

### 문제 1: "ModuleNotFoundError: No module named 'PySide6'"

**원인**: PySide6가 설치되지 않음

**해결**:
```bash
pip install PySide6
```

### 문제 2: "ImportError: cannot import name 'XXX'"

**원인**: 잘못된 디렉토리 구조 또는 누락된 __init__.py

**해결**:
1. 프로젝트 루트 디렉토리에서 실행하는지 확인
2. 모든 __init__.py 파일이 있는지 확인
3. 다시 설치:
```bash
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

### 문제 3: "Permission denied" 오류

**원인**: 파일 실행 권한 없음 (Linux/macOS)

**해결**:
```bash
chmod +x main.py
python main.py
```

### 문제 4: GUI 창이 표시되지 않음

**원인**: 디스플레이 설정 문제

**해결**:
1. **Linux**: X11 확인
   ```bash
   echo $DISPLAY
   # 결과가 비어있다면:
   export DISPLAY=:0
   ```

2. **macOS**: XQuartz 설치 (필요시)
   ```bash
   brew install --cask xquartz
   ```

3. **Windows**: 그래픽 드라이버 업데이트

### 문제 5: "netmiko not found" 경고

**원인**: 선택적 패키지 미설치 (정상 동작)

**해결**:
- 실시간 연결 기능이 필요한 경우:
  ```bash
  pip install netmiko paramiko
  ```
- GUI 구성 관리만 사용하는 경우: 무시 가능

### 문제 6: 한글 깨짐 (Windows)

**원인**: 콘솔 인코딩 문제

**해결**:
```cmd
chcp 65001
python main.py
```

또는 PowerShell 사용:
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
python main.py
```

## 첫 실행 체크리스트

애플리케이션을 처음 실행할 때:

- [ ] Python 3.8+ 설치 확인
- [ ] 가상환경 생성 및 활성화
- [ ] requirements.txt로 패키지 설치
- [ ] 프로젝트 루트 디렉토리에서 실행
- [ ] GUI 창이 정상적으로 표시되는지 확인
- [ ] 각 탭 클릭 가능 여부 확인

## 업그레이드

새 버전으로 업그레이드하려면:

```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 의존성 업데이트
pip install --upgrade -r requirements.txt

# 3. 실행
python main.py
```

## 제거

프로그램을 완전히 제거하려면:

```bash
# 1. 가상환경 비활성화
deactivate

# 2. 프로젝트 폴더 삭제
cd ..
rm -rf cisco-config-manager

# 3. 사용자 데이터 삭제 (선택적)
# Windows
rmdir /s %USERPROFILE%\.cisco_config_manager

# macOS/Linux
rm -rf ~/.cisco_config_manager
```

## 추가 도움말

더 많은 정보가 필요하신가요?

- **사용자 가이드**: README.md 참조
- **문제 보고**: GitHub Issues
- **이메일 지원**: support@example.com

---

**설치 완료!** 이제 `python main.py`로 애플리케이션을 실행하세요.
