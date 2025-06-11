import json
import subprocess
import platform
from pathlib import Path
from ..common.common import get_sam_path

def create_launch_json(port: int):
    vscode_path = Path(".vscode")
    vscode_path.mkdir(exist_ok=True)

    launch_config = \
    {
        "version": "0.2.0",
        "configurations": [
            {
            "name": "Infinite Debug Loop",
            "type": "debugpy",
            "request": "attach",
            "listen": {
                "host": "0.0.0.0",
                "port": 7789
            },
            "justMyCode": false,
            "pathMappings": [
                {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "/var/task"
                }
            ],
            "restart": true,
            "preLaunchTask": "Run Listener and Controller"
            },
            {
            "name": "Launch: program",
            "type": "python",
            "request": "launch",
            "console": "integratedTerminal",
            "program": "${file}",
            "logToFile": true,
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Launch: module",
            "type": "python",
            "request": "launch",
            "console": "integratedTerminal",
            "module": "${fileBasenameNoExtension}",
            "cwd": "${fileDirname}",
            "logToFile": true,
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Launch: code",
            "type": "python",
            "request": "launch",
            "console": "integratedTerminal",
            "code": ["import runpy", "runpy.run_path(r'${file}')"],
            "logToFile": true,
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Attach: connect",
            "type": "python",
            "request": "attach",
            "connect": {
                "port": 5678,
                "host": "127.0.0.1"
            },
            "logToFile": true,
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Attach: listen",
            "type": "python",
            "request": "attach",
            "listen": {
                "port": 5678,
                "host": "127.0.0.1"
            },
            "logToFile": true,
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Attach: PID",
            "type": "python",
            "request": "attach",
            "processId": "${command:pickProcess}",
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            },
            {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "console": "integratedTerminal",
            "purpose": ["debug-test"],
            "debugAdapterPath": "${workspaceFolder}/src/debugpy/adapter"
            }
        ]
    }

    with open(vscode_path / "launch.json", "w") as f:
        json.dump(launch_config, f, indent=4)
    print("✅ .vscode/launch.json 생성 완료")

def create_tasks_json():
    vscode_path = Path(".vscode")
    vscode_path.mkdir(exist_ok=True)

    tasks_config = \
    {
        "version": "2.0.0",
        "tasks": [
            {
            "label": "Run Listener and Controller",
            "type": "shell",
            "command": "python",
            "args": ["loop_controller.py"],
            "isBackground": true,
            "problemMatcher": {
                "owner": "custom",
                "pattern": [
                {
                    "regexp": "^listener\\.py:1:1:.*$",
                    "file": 1,
                    "line": 1,
                    "column": 1,
                    "message": 0
                }
                ],
                "background": {
                "activeOnStart": true,
                "beginsPattern": "listener.py:1:1: 디버깅 대기 중",
                "endsPattern": "디버깅 준비 완료"
                }
            },
            "presentation": { "reveal": "always", "panel": "shared" }
            }
        ]
    }

    with open(vscode_path / "tasks.json", "w") as f:
        json.dump(tasks_config, f, indent=4)
    print("✅ .vscode/tasks.json 생성 완료")

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
                "--app-template", "hello-world"
            ], check=True, cwd=Path.cwd()) # Ensure sam init runs in the current working directory
            print(f"✅ SAM 프로젝트 자동 생성 완료")

            # template.yaml 수정 시작
            template_file_path = Path.cwd() / "template.yaml"
            
            if not template_file_path.is_file():
                print(f"❌ template.yaml 파일을 찾을 수 없습니다: {template_file_path}")
            else:
                try:
                    with open(template_file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    new_lines = []
                    inserted = False
                    # 대상 라인 (정확한 문자열, 앞부분 공백 12칸)
                    target_line_content = "            Method: get"

                    for line in lines:
                        new_lines.append(line) # 현재 라인 추가
                        # 현재 라인(개행문자 제외)이 대상 라인인지 확인
                        if line.rstrip() == target_line_content:
                            if not inserted: # 첫 번째 일치하는 부분에만 삽입
                                indent_base = "            " # 공백 12칸
                                indent_param_item = "              " # 공백 14칸
                                new_lines.append(f"{indent_base}RequestParameters:\\n")
                                new_lines.append(f"{indent_param_item}- method.request.querystring.reinvoked\\n")
                                inserted = True
                    
                    if inserted:
                        with open(template_file_path, "w", encoding="utf-8") as f:
                            f.writelines(new_lines)
                        print(f"✅ template.yaml 수정 완료: RequestParameters 추가")
                    else:
                        print(f"⚠️ template.yaml 수정 실패: '{target_line_content}' 라인을 찾지 못했습니다. 파일 내용을 확인해주세요.")
                
                except Exception as e:
                    print(f"❌ template.yaml 수정 중 오류 발생: {e}")
            # template.yaml 수정 종료

        except subprocess.CalledProcessError as e:
            print(f"❌ SAM 프로젝트 생성 실패: {e}")
        except Exception as e: # Catch other potential errors during the process
            print(f"❌ SAM 템플릿 처리 중 예기치 않은 오류 발생: {e}")
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
    
    # tasks.json 생성
    create_tasks_json()

    # 방화벽 규칙 추가
    add_firewall_rule(port)

    # sam init 실행 방식 선택
    sam_mode = input("SAM 프로젝트를 자동 생성할까요? (Y/n): ").strip().lower()
    auto_mode = sam_mode != 'n'

    create_sam_template(auto_mode=auto_mode)

    print("🎉 buggerking init 완료!")
