# Cisco Config Manager

**Professional Cisco Network Configuration Management Tool**

Cisco 네트워크 장비 설정을 GUI로 관리하고, 실시간 연결을 통해 구성을 배포할 수 있는 전문가급 도구입니다.

## 📋 주요 기능

### 1. GUI 기반 구성 관리
- **8개 탭으로 구성된 직관적 인터페이스**
  - Global Settings (전역 설정)
  - Interface Configuration (인터페이스 설정)
  - VLAN Management (VLAN 관리)
  - Routing Protocols (라우팅 프로토콜)
  - Switching Features (스위칭 기능)
  - Security Settings (보안 설정)
  - ACL Management (접근 제어 목록)
  - High Availability (고가용성)

### 2. 실시간 장비 연결
- **SSH/Telnet 프로토콜 지원**
- **다중 장비 동시 관리**
- **실시간 명령어 실행**
- **구성 자동 배포**

### 3. 지능형 구성 분석
- **Show Run 출력 자동 분석**
- **기존 구성 Import**
- **변경사항 자동 감지**
- **Diff 뷰어**

### 4. 명령어 자동 생성
- **GUI 설정 → Cisco CLI 명령어 변환**
- **IOS, IOS-XE, NX-OS 지원**
- **구성 검증 및 미리보기**

### 5. 템플릿 시스템
- **재사용 가능한 구성 템플릿**
- **내장 템플릿 제공**
  - Basic Access Switch
  - Core Switch
  - Distribution Switch
  - Edge Router
  - Data Center Switch
- **사용자 정의 템플릿 저장/불러오기**

### 6. 입력 검증
- **실시간 입력값 검증**
- **IP 주소, 서브넷 마스크, VLAN ID 등**
- **잘못된 입력 즉시 감지**

## 🚀 시작하기

### 필수 요구사항

- **Python 3.8 이상**
- **운영체제**: Windows, macOS, Linux

### 설치 방법

1. **저장소 클론**
```bash
git clone https://github.com/yourusername/cisco-config-manager.git
cd cisco-config-manager
```

2. **가상환경 생성 (권장)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **의존성 설치**
```bash
pip install -r requirements.txt
```

### 실행 방법

```bash
python main.py
```

## 📁 프로젝트 구조

```
cisco-config-manager/
│
├── main.py                      # 애플리케이션 진입점
├── requirements.txt             # Python 의존성
├── README.md                    # 프로젝트 문서
│
├── ui/                          # UI 모듈
│   ├── __init__.py
│   ├── main_window.py          # 메인 윈도우
│   ├── device_manager_dialog.py # 장비 연결 관리
│   ├── dialogs.py              # 입력 다이얼로그들
│   │
│   └── tabs/                   # 탭 모듈들
│       ├── __init__.py
│       ├── global_tab.py       # 전역 설정 탭
│       ├── interface_tab.py    # 인터페이스 탭
│       ├── vlan_tab.py         # VLAN 탭
│       ├── routing_tab.py      # 라우팅 탭
│       ├── switching_tab.py    # 스위칭 탭
│       ├── security_tab.py     # 보안 탭
│       ├── acl_tab.py          # ACL 탭
│       └── ha_tab.py           # 고가용성 탭
│
└── core/                        # 핵심 로직
    ├── __init__.py
    ├── cli_analyzer.py         # CLI 출력 분석기
    ├── command_generator.py    # 명령어 생성기
    ├── config_diff.py          # 구성 비교
    ├── connection_manager.py   # 장비 연결 관리
    ├── templates.py            # 템플릿 관리
    └── validators.py           # 입력 검증
```

## 💡 사용 예시

### 1. 새 스위치 구성

1. **메인 윈도우 실행**
2. **Global 탭에서 기본 설정**
   - Hostname: SW-ACCESS-01
   - Domain Name: company.local
3. **VLAN 탭에서 VLAN 생성**
   - VLAN 10: Users
   - VLAN 20: Servers
   - VLAN 30: Guest
4. **Interface 탭에서 포트 설정**
   - Gi0/1-24: Access VLAN 10
   - Gi0/25-48: Access VLAN 20
5. **Preview & Generate 클릭**
6. **생성된 명령어 확인 및 저장**

### 2. 기존 구성 Import

1. **File → Import → Show Run Text**
2. **Show run 출력 붙여넣기**
3. **자동으로 각 탭에 구성 로드**
4. **필요한 부분 수정**
5. **변경사항 미리보기**

### 3. 실시간 장비 연결

1. **Tools → Device Manager**
2. **Add Device 클릭**
3. **장비 정보 입력**
   - IP Address: 192.168.1.1
   - Device Type: cisco_ios
   - Username: admin
4. **Connect 클릭**
5. **명령어 실행 또는 구성 배포**

### 4. 템플릿 사용

1. **File → Templates → Load Template**
2. **"Basic Access Switch" 선택**
3. **자동으로 기본 구성 로드**
4. **필요에 맞게 커스터마이징**
5. **File → Templates → Save as Template**

## 🔧 고급 기능

### Undo/Redo 지원
- **Ctrl+Z**: Undo
- **Ctrl+Y**: Redo
- 모든 변경사항 추적

### 구성 비교
- **Original vs Modified 비교**
- **변경사항 하이라이트**
- **Diff 리포트 생성**

### 일괄 배포
- **여러 장비에 동일 구성 배포**
- **진행 상황 실시간 모니터링**
- **배포 결과 로그**

### 구성 검증
- **문법 오류 체크**
- **논리적 충돌 감지**
- **Best Practice 권장사항**

## 🛠 기술 스택

- **GUI Framework**: PySide6 (Qt for Python)
- **Network Library**: Netmiko, Paramiko
- **Data Format**: JSON, YAML
- **Language**: Python 3.8+

## 📝 의존성

### 필수 라이브러리

```txt
PySide6>=6.5.0              # GUI Framework
PyYAML>=6.0                 # YAML 처리
```

### 선택적 라이브러리 (실시간 연결 기능)

```txt
netmiko>=4.1.0             # 네트워크 장비 연결
paramiko>=2.11.0           # SSH 연결
textfsm>=1.1.0             # CLI 출력 파싱
```

## 🎯 지원 플랫폼

### Cisco 플랫폼
- ✅ **Cisco IOS** (15.x)
- ✅ **Cisco IOS-XE** (16.x, 17.x)
- ✅ **Cisco NX-OS** (7.x, 9.x)
- ⚠️ **Cisco ASA** (부분 지원)

### 기능 지원 매트릭스

| 기능 | IOS | IOS-XE | NX-OS |
|-----|-----|--------|-------|
| 인터페이스 | ✅ | ✅ | ✅ |
| VLAN | ✅ | ✅ | ✅ |
| Routing | ✅ | ✅ | ✅ |
| ACL | ✅ | ✅ | ✅ |
| StackWise Virtual | ❌ | ✅ | ❌ |
| vPC | ❌ | ❌ | ✅ |

## 🐛 문제 해결

### 연결 문제

**증상**: SSH 연결 실패
```
해결방법:
1. 장비 IP 주소 확인
2. SSH가 활성화되어 있는지 확인
3. 인증 정보 확인
4. 네트워크 연결 확인
```

### Import 문제

**증상**: Show run이 제대로 파싱되지 않음
```
해결방법:
1. 전체 show run 출력 복사 (building configuration... 포함)
2. 특수 문자 제거
3. 최신 버전 업데이트
```

### GUI 문제

**증상**: 윈도우가 표시되지 않음
```
해결방법:
1. PySide6 재설치: pip install --upgrade PySide6
2. 디스플레이 설정 확인
3. Python 버전 확인 (3.8 이상 필요)
```

## 📚 문서

- **사용자 가이드**: [docs/user-guide.md](docs/user-guide.md) (예정)
- **개발자 문서**: [docs/developer.md](docs/developer.md) (예정)
- **API 레퍼런스**: [docs/api-reference.md](docs/api-reference.md) (예정)

## 🤝 기여하기

프로젝트 기여를 환영합니다!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 👤 작성자

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

## 🙏 감사의 말

- Cisco Systems for network equipment documentation
- PySide6/Qt community
- Netmiko contributors
- All open source contributors

## 📈 버전 히스토리

### v1.0.0 (2024-01-XX)
- 초기 릴리스
- 기본 GUI 구성 관리
- Show run import 기능
- 명령어 생성 기능

### v1.1.0 (계획)
- 실시간 장비 연결
- 일괄 배포 기능
- 구성 검증 강화

### v1.2.0 (계획)
- Ansible 통합
- 웹 인터페이스
- 고급 템플릿 엔진

## 💬 지원

문제가 발생하거나 질문이 있으신 경우:
- **Issues**: [GitHub Issues](https://github.com/yourusername/cisco-config-manager/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cisco-config-manager/discussions)
- **Email**: support@example.com

---

**⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!**

**Made with ❤️ for Network Engineers**
