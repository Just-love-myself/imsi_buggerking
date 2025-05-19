import json
import subprocess
import platform
from pathlib import Path
from ..common.common import get_sam_path

def create_launch_json(port: int):
    vscode_path = Path(".vscode")
    vscode_path.mkdir(exist_ok=True)

    launch_config = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Remote Debug (Lambda)",
                "type": "python",
                "request": "attach",
                "listen": {
                    "host": "0.0.0.0",
                    "port": port
                },
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}",
                        "remoteRoot": "/var/task"
                    }
                ]
            }
        ]
    }

    with open(vscode_path / "launch.json", "w") as f:
        json.dump(launch_config, f, indent=4)
    print("✅ .vscode/launch.json 생성 완료")

def add_firewall_rule(port: int):
    if platform.system() != "Windows":
        print("⚠️ 이 기능은 Windows에서만 동작합니다.")
        return

    print(f"🛡️ 방화벽 인바운드 규칙을 추가하려면 관리자 권한이 필요합니다. 잠시 후 UAC 알림창이 뜰 수 있습니다...")

    ps_script = f'''
    New-NetFirewallRule -DisplayName "buggerking-TCP-{port}" -Direction Inbound -Protocol TCP -LocalPort {port} -Action Allow
    New-NetFirewallRule -DisplayName "buggerking-UDP-{port}" -Direction Inbound -Protocol UDP -LocalPort {port} -Action Allow
    '''

    # PowerShell 관리자 권한으로 실행 + 방화벽 규칙 등록
    try:
        subprocess.run([
            "powershell",
            "-Command",
            f'Start-Process powershell -Verb runAs -ArgumentList \'-Command {ps_script}\''
        ], check=True)
        print(f"✅ 관리자 권한으로 방화벽 인바운드 규칙 추가 완료 (TCP/UDP 포트 {port})")
    except subprocess.CalledProcessError as e:
        print(f"❌ 방화벽 규칙 추가 실패: {e}")

def create_sam_template(project_name="buggerking_remote_debugger", auto_mode=True):
    sam_path = get_sam_path()
    print(f"🔍 SAM CLI 경로: {sam_path}")
    if auto_mode:
        print("📦 SAM 템플릿을 자동으로 생성 중입니다...")

        try:
            subprocess.run([
                sam_path,
                "init",
                "--no-interactive",
                "--runtime", "python3.13",
                "--dependency-manager", "pip",
                "--app-template", "hello-world",
                "--name", project_name
            ], check=True)
            print(f"✅ SAM 프로젝트 자동 생성 완료: {project_name}")
        except subprocess.CalledProcessError as e:
            print(f"❌ SAM 프로젝트 생성 실패: {e}")
    else:
        print("🛠️ SAM CLI 인터랙티브 모드를 실행합니다.")
        try:
            subprocess.run(["sam", "init"], check=True)
            print("✅ SAM 프로젝트 수동 생성 완료")
        except subprocess.CalledProcessError as e:
            print(f"❌ SAM 인터랙티브 모드 실패: {e}")


def init():
    print("🔧 buggerking 초기 설정을 시작합니다...")

    # 포트 입력
    try:
        port_input = input("원격 디버깅용 포트 번호를 입력하세요 (예: 7789): ")
        port = int(port_input)
    except ValueError:
        print("❌ 유효한 숫자를 입력해주세요.")
        return

    # launch.json 생성
    create_launch_json(port)

    # 방화벽 규칙 추가
    add_firewall_rule(port)

    # sam init 실행 방식 선택
    sam_mode = input("SAM 프로젝트를 자동 생성할까요? (Y/n): ").strip().lower()
    auto_mode = sam_mode != 'n'

    create_sam_template(auto_mode=auto_mode)

    print("🎉 buggerking init 완료!")
