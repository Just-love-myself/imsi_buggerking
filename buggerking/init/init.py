import json
import subprocess
import platform
import os
from pathlib import Path
from ..common.common import get_sam_path

def create_launch_json(port: int):
    vscode_path = Path(".vscode")
    vscode_path.mkdir(exist_ok=True)

    launch_json_content = f"""{{
  // Use IntelliSense to learn about possible attributes.
  // Hover to view descriptions of existing attributes.
  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
  "version": "0.2.0",
  "configurations": [
    {{
      "name": "Infinite Debug Loop",
      "type": "debugpy",
      "request": "attach",
      "listen": {{
        "host": "0.0.0.0",
        "port": {port}
      }},
      "justMyCode": false,
      "pathMappings": [
        {{
          "localRoot": "${{workspaceFolder}}",
          "remoteRoot": "/var/task"
        }}
      ],
      "restart": true,
      "preLaunchTask": "Run Listener and Controller"
    }},
    {{
      "name": "Launch: program",
      "type": "python",
      "request": "launch",
      "console": "integratedTerminal",
      "program": "${{file}}",
      "logToFile": true,
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Launch: module",
      "type": "python",
      "request": "launch",
      "console": "integratedTerminal",
      "module": "${{fileBasenameNoExtension}}",
      "cwd": "${{fileDirname}}",
      "logToFile": true,
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Launch: code",
      "type": "python",
      "request": "launch",
      "console": "integratedTerminal",
      "code": ["import runpy", "runpy.run_path(r\\'${{file}}\\'')"],
      "logToFile": true,
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Attach: connect",
      "type": "python",
      "request": "attach",
      "connect": {{
        "port": 5678,
        "host": "127.0.0.1"
      }},
      "logToFile": true,
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Attach: listen",
      "type": "python",
      "request": "attach",
      "listen": {{
        "port": 5678,
        "host": "127.0.0.1"
      }},
      "logToFile": true,
      //"restart": true,
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Attach: PID",
      "type": "python",
      "request": "attach",
      "processId": "${{command:pickProcess}}",
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }},
    {{
      "name": "Debug Tests",
      "type": "python",
      "request": "launch",
      "console": "integratedTerminal",
      "purpose": ["debug-test"],
      "debugAdapterPath": "${{workspaceFolder}}/src/debugpy/adapter"
    }}
  ]
}}"""

    file_path = vscode_path / "launch.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(launch_json_content)
    print("✅ .vscode/launch.json 생성 완료")

def create_tasks_json():
    vscode_path = Path(".vscode")
    vscode_path.mkdir(exist_ok=True)

    tasks_json_content = f"""{{
    "version": "2.0.0",
    "tasks": [
        {{
            "label": "Run Listener and Controller",
            "type": "shell",
            "command": "python",
            "args": ["loop_controller.py"],
            "isBackground": true,
            "problemMatcher": {{
                "owner": "custom",
                "pattern": [
                    {{
                        "regexp": "^listener\\\\\\\\.py:1:1:.*$",
                        "file": 1,
                        "line": 1,
                        "column": 1,
                        "message": 0
                    }}
                ],
                "background": {{
                    "activeOnStart": true,
                    "beginsPattern": "listener.py:1:1: 디버깅 대기 중",
                    "endsPattern": "디버깅 준비 완료"
                }}
            }},
            "presentation": {{ "reveal": "always", "panel": "shared" }}
        }}
    ]
}}"""

    file_path = vscode_path / "tasks.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(tasks_json_content)
    print("✅ .vscode/tasks.json 생성 완료")

def create_loop_controller():
    vscode_path = Path(".")
    vscode_path.mkdir(exist_ok=True)

    loop_controller_content = f"""# loop_controller.py
import subprocess
import time
import psutil
import socket
import sys
import signal
import os
import requests
from typing import Any, Tuple, cast
from threading import Thread

from .listener import main as listener_main


LISTENER_SCRIPT = "listener.py"
DEBUGPY_PORT    = 7789   # VSCode debug adapter listen 포트
SHUTDOWN_CODE   = 123
listener_proc   = None
listener_thread = None
func_result = [0, '']  # [exit_code, func gateway url]

# debugpy 프로세스(자식) 정리; Pylance 경고 무시용 캐스트 포함
def kill_debugpy():
    for conn in psutil.net_connections(kind="inet"):
        laddr = conn.laddr
        if isinstance(laddr, tuple):
            addr_tuple = cast(Tuple[Any, Any], laddr)
            port = addr_tuple[1]
        else:
            port = getattr(laddr, "port", None)
        if conn.status == psutil.CONN_LISTEN and port == DEBUGPY_PORT and conn.pid:
            try:
                print(f"[🔪] debugpy 종료: PID={conn.pid} on port {DEBUGPY_PORT}")
                psutil.Process(conn.pid).kill()
            except:
                pass

def handle_sigint(signum, frame):
    print("\n[⚠️] Ctrl+C 감지—loop_controller 종료")
    if listener_proc and listener_proc.poll() is None:
        listener_proc.kill()
    if listener_thread and listener_thread.is_alive():
        listener_thread.terminate()
    # debugpy 프로세스 정리
    kill_debugpy()
    os._exit(0)

signal.signal(signal.SIGINT, handle_sigint)

# listener.py 프로세스 실행
def start_listener():
    global listener_proc, listener_thread, func_gateway
    # 혹시 떠 있는 구 버전 listener.py 있으면 정리
    for proc in psutil.process_iter(['pid','cmdline']):
        try:
            if LISTENER_SCRIPT in ' '.join(proc.info.get('cmdline') or []):
                proc.kill()
        except:
            pass
    # listener_proc = subprocess.Popen([sys.executable, LISTENER_SCRIPT])
    # return listener_proc
    listener_thread = Thread(target=listener_main, args=(func_result,), daemon=True)
    listener_thread.start()
    return listener_thread

# VSCode debug adapter(attach listen)가 포트 열릴 때까지 대기
def wait_for_debugpy():
    print(f"[🕓] 디버거 포트({DEBUGPY_PORT}) 연결 대기 중...")
    while True:
        if listener_proc and listener_proc.poll() is not None:
            return False
        elif listener_thread and not listener_thread.is_alive():
            return False
        try:
            with socket.create_connection(("localhost", DEBUGPY_PORT), timeout=1):
                print("[✅] 디버거 연결 확인됨!")
                return True
        except:
            time.sleep(0.1)

# Lambda 호출 (예외 트리거 & remote attach 유도)
def invoke_lambda():
    url = f'{func_result[1]}?reinvoked=true'
    print("[🌐] Lambda 호출 중...")
    try:
        resp = requests.post(url, json={})
        print(f"[✅] 호출 완료: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"[❗] 호출 실패: {e}")

def main():
    print("[▶️] Infinite debug loop 시작")
    first_run = True                  # <-- 처음 플래그
    try:
        while True:
            listener_th = start_listener()

            # 1) VSCode debug adapter가 listen 중인지 확인
            if not wait_for_debugpy():
                print("[❌] listener.py가 중단됨—전체 종료")
                break

            # 2) 첫 실행이면 invoke_lambda 스킵, 이후부터 호출
            if first_run:
                print("[ℹ️] 첫 디버깅 세션—Lambda 호출 건너뜀")
                first_run = False
            else:
                invoke_lambda()

            # 3) listener.py(타이머 서버) 종료 대기
            listener_th.join()
            print(f"[ℹ️] listener.py 종료 (code={func_result[0]}, url={func_result[1]})")

            kill_debugpy()

            # 4) Lambda(어댑터)에서 보낸 shutdown 신호면 전체 종료
            if func_result[0] == SHUTDOWN_CODE:
                print("[✅] Shutdown signal 처리—전체 종료")
                break

            print("[⚠️] listener.py 비정상 종료—3초 후 재시작")
            time.sleep(3)

    except KeyboardInterrupt:
        handle_sigint(None, None)
    finally:
        os._exit(0)

if __name__ == "__main__":
    main()
"""

    file_path = vscode_path / "loop_controller.py"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(loop_controller_content)
    print("✅ loop_controller.py 생성 완료")
    
def create_listener():
    vscode_path = Path(".")
    vscode_path.mkdir(exist_ok=True)
    
    listener_content = f'''# listener.py - 8바이트 헤더 방식 적용된 완전한 버전
import socket
import json
import struct  # 추가: 8바이트 헤더 처리용
import threading
import time
import sys
import os
import datetime
import signal

PORT = 6689
SHUTDOWN_CODE = 123
sock = None
shutdown_flag = threading.Event()  # 스레드 간 shutdown 신호 공유

# 디버그 데이터 저장 폴더 설정
DEBUG_DATA_DIR = "debug_data"

# Ctrl+C 핸들러: 수동 종료
def handle_sigint(signum, frame):
    print("\n[⚠️] Ctrl+C 감지—listener 종료")
    if sock:
        try:
            sock.close()
            print("[✖️] 리스닝 소켓 닫음")
        except:
            pass
    
    # shutdown 플래그가 설정되어 있으면 SHUTDOWN_CODE로 종료
    exit_code = SHUTDOWN_CODE if shutdown_flag.is_set() else 0
    print(f"[🔚] 종료 코드: {exit_code}")
    os._exit(exit_code)

signal.signal(signal.SIGINT, handle_sigint)

# # 디버그 데이터 저장 함수
# def save_debug_data(data_type, filename, content, file_size):
#     """Lambda에서 전송된 디버그 데이터를 파일로 저장"""
#     try:
#         # 디버그 데이터 폴더 생성
#         if not os.path.exists(DEBUG_DATA_DIR):
#             os.makedirs(DEBUG_DATA_DIR)
#             print(f"[📁] 생성됨: {DEBUG_DATA_DIR}")
        
#         # 타임스탬프 추가한 파일명 생성
#         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
#         # 파일명 처리 (확장자 유지)
#         if '.' in filename:
#             name, ext = filename.rsplit('.', 1)
#             safe_filename = f"{timestamp}_{name}.{ext}"
#         else:
#             safe_filename = f"{timestamp}_{filename}.json"
        
#         file_path = os.path.join(DEBUG_DATA_DIR, safe_filename)
        
#         # 파일 저장
#         with open(file_path, 'w', encoding='utf-8') as f:
#             if isinstance(content, str):
#                 f.write(content)
#             else:
#                 json.dump(content, f, indent=2, ensure_ascii=False)
        
#         actual_size = os.path.getsize(file_path)
        
#         print(f"[💾] 파일 저장 완료!")
#         print(f"    📂 경로: {file_path}")
#         print(f"    📊 타입: {data_type}")
#         print(f"    📏 크기: {actual_size} bytes (전송: {file_size} bytes)")
#         print(f"    📅 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
#         return True
        
#     except Exception as e:
#         print(f"[❌] 파일 저장 실패: {e}")
#         import traceback
#         print(f"[❌] 상세 오류: {traceback.format_exc()}")
#         return False

def save_debug_data(payload):
    """Lambda에서 전송된 디버그 데이터를 파일로 저장"""
    try:
        # 디버그 데이터 폴더 생성
        if not os.path.exists(DEBUG_DATA_DIR):
            os.makedirs(DEBUG_DATA_DIR)
            print(f"[📁] 생성됨: {DEBUG_DATA_DIR}")
        
        # 타임스탬프 추가한 파일명 생성
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_unified_callstack.json"
        file_path = os.path.join(DEBUG_DATA_DIR, filename)
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            if isinstance(payload, str):
                f.write(payload)
            else:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        
        actual_size = os.path.getsize(file_path)
        
        print(f"[💾] 파일 저장 완료!")
        print(f"    📂 경로: {file_path}")
        print(f"    📊 타입: unified_callstack")
        print(f"    📏 크기: {actual_size} bytes")
        print(f"    📅 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"[❌] 파일 저장 실패: {e}")
        import traceback
        print(f"[❌] 상세 오류: {traceback.format_exc()}")
        return False

# 남은 시간 출력 루프
def print_remaining_time(initial_ms):
    print(f"[⏱️] 타이머 시작됨 (초기값: {initial_ms} ms)")
    start = time.time()
    warned = False
    while True:
        # shutdown 플래그 확인
        if shutdown_flag.is_set():
            print("[🔚] Shutdown 신호로 타이머 중단")
            return
            
        elapsed = int((time.time() - start) * 1000)
        remaining = max(0, initial_ms - elapsed)
        if not warned and remaining <= 5000:
            print("⚠️ 경고: 타임아웃까지 5초 남았습니다!")
            warned = True
        print(f"[⏱️] 남은 시간: {remaining} ms")
        if remaining <= 0:
            print("❌ 타이머 종료—listener 재시작")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        time.sleep(0.5)

def send_dap_message(sock, data, message_type_str: str):
    """
    지정된 타입과 데이터를 사용하여 고정 크기 헤더와 가변 크기 바디로 구성된 메시지를 전송합니다.
    헤더는 4바이트 메시지 타입 문자열과 4바이트 바디 크기 정수로 구성됩니다. (총 8바이트 헤더)
    수신측에서는 이 헤더를 먼저 읽고 파싱하여 바디의 크기를 알아낸 후, 해당 크기만큼 바디를 읽습니다.

    :param sock: 소켓 객체
    :param data: 전송할 데이터 (dict만 지원 - 자동으로 JSON 변환됨)
    :param message_type_str: 메시지 타입을 나타내는 4자리 문자열 (예: "TIME", "SHUT", "CAPT").
                             4자보다 짧으면 공백으로 패딩되고, 길면 4자로 절단됩니다.
    :return: 성공 시 True, 실패 시 False
    """
    try:
        # 모든 데이터는 dict → JSON으로 처리 (프로토콜 단순화)
        if isinstance(data, dict):
            body_bytes = json.dumps(data).encode('utf-8')
        else:
            error_msg = f"Unsupported data type: {type(data)}. Only dict is supported (automatically converted to JSON)."
            print(f"❌ [DAP-SEND] 데이터 타입 오류 ({message_type_str}): {error_msg}")
            raise TypeError(error_msg)

        body_length = len(body_bytes)

        # 헤더 생성 (총 8바이트)
        # 1. 메시지 타입 (4바이트 ASCII)
        type_str_fixed_length = message_type_str.ljust(4)[:4]
        type_bytes_for_header = type_str_fixed_length.encode('ascii')

        # 2. 바디 길이 (4바이트 big-endian unsigned integer)
        body_length_bytes = struct.pack('>I', body_length)

        header_bytes = type_bytes_for_header + body_length_bytes
        
        message_to_send = header_bytes + body_bytes
        sock.sendall(message_to_send)
        
        total_sent = len(message_to_send)
        print(f"📤 [DAP-SEND] '{message_type_str}' 전송 완료: header={len(header_bytes)}B, body={body_length}B. 총 {total_sent}B.")
        return True
        
    except TypeError: 
        return False 
    except Exception as e:
        print(f"❌ [DAP-SEND] '{message_type_str}' 전송 실패 (오류: {type(e).__name__}): {e}")
        return False

def receive_dap_message(conn):
    """
    고정 크기 헤더와 가변 크기 바디로 구성된 메시지를 수신합니다.
    헤더는 4바이트 메시지 타입 문자열과 4바이트 바디 크기 정수로 구성됩니다. (총 8바이트 헤더)
    
    :param conn: 소켓 연결 객체
    :return: 성공 시 (message_type, data) 튜플, 실패 시 None
    """
    try:
        # 1단계: 헤더 8바이트 수신
        header_bytes = _receive_exact_bytes(conn, 8)
        if header_bytes is None:
            print("❌ [DAP-RECV] 헤더 수신 실패")
            return None
        
        # 2단계: 헤더 파싱
        # 메시지 타입 (4바이트 ASCII)
        type_bytes = header_bytes[:4]
        message_type = type_bytes.decode('ascii').rstrip()  # 오른쪽 공백 제거
        
        # 바디 길이 (4바이트 big-endian unsigned integer)
        body_length_bytes = header_bytes[4:8]
        body_length = struct.unpack('>I', body_length_bytes)[0]
        
        print(f"📥 [DAP-RECV] 헤더 파싱 완료: type='{message_type}', body_length={body_length}B")
        
        # 3단계: 바디 수신 (길이가 0이면 빈 바이트)
        if body_length == 0:
            body_bytes = b''
        else:
            body_bytes = _receive_exact_bytes(conn, body_length)
            if body_bytes is None:
                print(f"❌ [DAP-RECV] 바디 수신 실패 (예상: {body_length}B)")
                return None
        
        # 4단계: JSON 데이터 변환
        json_str = body_bytes.decode('utf-8')
        data = json.loads(json_str)
        
        total_received = 8 + body_length
        print(f"📥 [DAP-RECV] '{message_type}' 수신 완료: header=8B, body={body_length}B. 총 {total_received}B.")
        
        return (message_type, data)
        
    except json.JSONDecodeError as e:
        print(f"❌ [DAP-RECV] JSON 파싱 실패: {e}")
        return None
    except UnicodeDecodeError as e:
        print(f"❌ [DAP-RECV] UTF-8 디코딩 실패: {e}")
        return None
    except Exception as e:
        print(f"❌ [DAP-RECV] 수신 실패 (오류: {type(e).__name__}): {e}")
        return None

def _receive_exact_bytes(conn, num_bytes):
    """
    소켓에서 정확히 지정된 바이트 수만큼 데이터를 수신합니다.
    """
    received_data = b''
    remaining_bytes = num_bytes
    
    while remaining_bytes > 0:
        try:
            chunk = conn.recv(remaining_bytes)
            if not chunk:  # 연결이 닫힌 경우
                print(f"❌ [DAP-RECV] 연결 종료됨 (수신된: {len(received_data)}B, 예상: {num_bytes}B)")
                return None
            
            received_data += chunk
            remaining_bytes -= len(chunk)
            
        except Exception as e:
            print(f"❌ [DAP-RECV] 바이트 수신 오류: {e}")
            return None
    
    return received_data

def find_latest_callstack_file():
    """가장 최근의 callstack 파일 찾기"""
    try:
        print(f"🔍 [FILE-SEARCH] {DEBUG_DATA_DIR} 폴더에서 파일 검색...")

        if not os.path.exists(DEBUG_DATA_DIR):
            print(f"❌ [FILE-SEARCH] 폴더 없음: {DEBUG_DATA_DIR}")
            return None
        
        debug_files = []
        all_files = os.listdir(DEBUG_DATA_DIR)
        print(f"📁 [FILE-SEARCH] 전체 파일 개수: {len(all_files)}")
        
        for filename in all_files:
            if "unified_callstack" in filename and filename.endswith('.json'):
                filepath = os.path.join(DEBUG_DATA_DIR, filename)
                mtime = os.path.getmtime(filepath)
                file_size = os.path.getsize(filepath)
                
                debug_files.append((mtime, filepath, filename, file_size))
                print(f"✅ [FILE-SEARCH] callstack 파일 발견: {filename} ({file_size} bytes)")
        
        if debug_files:
            # 시간순 정렬 (최신 순)
            debug_files.sort(reverse=True)
            latest_file = debug_files[0]

            print(f"🏆 [FILE-SEARCH] 최신 파일: {latest_file[2]}")
            print(f"🏆 [FILE-SEARCH] 수정 시간: {datetime.datetime.fromtimestamp(latest_file[0])}")
            print(f"🏆 [FILE-SEARCH] 파일 크기: {latest_file[3]} bytes")

            return latest_file[1]  # 파일 경로 반환
        
        print(f"❌ [FILE-SEARCH] callstack 파일 없음")
        return None
        
    except Exception as e:
        print(f"❌ [FILE-SEARCH] 검색 오류: {e}")
        return None

def handle_timeout_and_send_json(payload, conn, addr, shared_result):
    """타이머 + JSON 파일 전송 (연결 유지) - 8바이트 헤더 방식"""
    remaining_ms = int(payload.get('remaining_ms', 0))
    shared_result[1] = payload.get('api_gateway_url', 'Wrong URL')
    print(f"📨 [JSON-SEND] Timeout 신호 수신 from {addr} | timeout: {remaining_ms} ms | api_gateway_url: {shared_result[1]}")
    
    # 1) 타이머 스레드 시작
    threading.Thread(
        target=print_remaining_time,
        args=(remaining_ms,),
        daemon=True
    ).start()
    
    # 2) JSON 파일 찾기 및 전송
    latest_file = find_latest_callstack_file()
    
    if latest_file:
        print(f"📤 [JSON-SEND] JSON 파일 발견: {os.path.basename(latest_file)}")
        
        try:
            # 파일 크기 확인
            file_size = os.path.getsize(latest_file)
            print(f"📤 [JSON-SEND] 파일 크기: {file_size} bytes")
            
            # JSON 파일 읽기
            with open(latest_file, 'r', encoding='utf-8') as f:
                json_content = f.read()
                json_dict = json.loads(json_content)  # str → dict 변환
            
            print(f"📤 [JSON-SEND] 파일 내용 읽기 완료: {len(json_content)} chars")
            
            # 8바이트 헤더 방식으로 전송 (JSON 타입)
            success = send_dap_message(conn, json_dict, "CAPT")
            
            if success:
                print(f"✅ [JSON-SEND] 전송 완료! 총 {len(json_content)} chars")
            else:
                print(f"❌ [JSON-SEND] 전송 실패!")
            
        except Exception as e:
            print(f"❌ [JSON-SEND] 전송 실패: {e}")
            import traceback
            print(f"❌ [JSON-SEND] 상세: {traceback.format_exc()}")
    
    else:
        print(f"❌ [JSON-SEND] 전송할 JSON 파일 없음")

# Lambda에서 보내는 연결(타이머 / shutdown / 파일 저장 / 상태 복구) 처리
def handle_connection(conn, addr, shared_result):
    global sock
    try:
        print(f"[🔗] 연결됨: {addr}")
        
        # 8바이트 헤더 방식으로 메시지 수신
        result = receive_dap_message(conn)
        
        if not result:
            print(f"[❗] 메시지 수신 실패 from {addr}")
            return
        
        message_type, data = result
        print(f"[📥] 수신된 메시지 타입: '{message_type}', 데이터 타입: {type(data)}")
        
            
        # 🔥 특별 처리: remaining_ms 신호면 연결 유지하고 JSON 전송
        if message_type.upper() == 'TIME' and 'remaining_ms' in data:
            handle_timeout_and_send_json(data, conn, addr, shared_result)
            return
            
        # 일반 처리 (CAPT, SHUT, EROR 등)
        handle_payload(data, addr, message_type)
                
    except Exception as e:
        print(f"[❗] 연결 처리 오류 from {addr}: {e}")
        import traceback
        print(f"[❗] 상세 오류: {traceback.format_exc()}")
    finally:
        try:
            conn.close()
        except:
            pass

def handle_payload(payload, addr, message_type):
    """페이로드 타입별 처리"""
    try:
        print(f"📥 [PAYLOAD] 페이로드 수신 from {addr}: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}")
        
        # 1. Shutdown 신호 처리
        if message_type.upper() == 'SHUT':
            print(f"🚨 Shutdown signal 수신 from {addr}")
            shutdown_flag.set()  # 플래그 설정
            
            # 메인 스레드가 정리할 수 있도록 잠시 대기
            time.sleep(0.1)
            
            print(f"🔚 Shutdown 처리 완료 - 메인 스레드로 제어 이관")
            return
        
        # 2. 파일 저장 처리
        elif message_type.upper() == 'CAPT':
            print(f"📥 캡처 데이터 수신 from {addr}")
            # 파일 저장 (payload만 전달)
            success = save_debug_data(payload)
            
            if success:
                print(f"✅ 파일 저장 성공")
            else:
                print(f"❌ 파일 저장 실패")

            return
        
        else:
            # 3. 기타 타입(EROR, EMPT 등) 처리
            raise ValueError(f"잘못된 메시지 타입: {message_type}")
        
        
        # # 일반적인 디버그 데이터로 저장 시도
        # if len(payload) > 1:  # 단순 신호가 아니면
        #     filename = f"unknown_data_{int(time.time())}.json"
        #     save_debug_data("unknown", filename, payload, 0)
        
    except Exception as e:
        print(f"[❗] 페이로드 처리 오류 from {addr}: {e}")

def main(shared_result):
    global sock
    
    print(f"""
🚀 Enhanced Listener 시작 (8바이트 헤더 방식 적용)
📅 시간: {datetime.datetime.now()}
📂 저장 폴더: {DEBUG_DATA_DIR}
🌐 리스닝 포트: {PORT}
🔧 통신 방식: 8바이트 헤더 (4바이트 타입 + 4바이트 길이)
""")
    
    # 문제 매처를 위해 반드시 이 두 줄을 찍습니다.
    print("listener.py:1:1: 디버깅 대기 중")
    print("디버깅 준비 완료")

    # 타이머 수신용 TCP 서버
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))
    sock.listen(5)  # 큐 크기 증가
    sock.settimeout(1.0)

    try:
        while True:
            # shutdown 플래그 확인
            if shutdown_flag.is_set():
                print("[🔚] Shutdown 플래그 감지 - 메인 루프 종료")
                break
                
            try:
                conn, addr = sock.accept()
                print(f"[🔗] 새 연결: {addr}")
            except socket.timeout:
                continue
            except OSError:
                # 소켓이 닫혔을 때 shutdown 플래그 확인
                if shutdown_flag.is_set():
                    print("[🔚] Shutdown으로 인한 소켓 종료")
                    break
                else:
                    print("[❗] 예상치 못한 소켓 오류")
                    break
                    
            # 각 연결을 별도 스레드에서 처리
            threading.Thread(
                target=handle_connection,
                args=(conn, addr, shared_result),
                daemon=True
            ).start()
            
    except KeyboardInterrupt:
        print("\n[⚠️] Ctrl+C로 인한 종료")
    finally:
        if sock:
            sock.close()
            print("[✖️] 리스닝 소켓 닫음 (finally)")
        
        # shutdown 플래그에 따른 종료 코드 결정
        exit_code = SHUTDOWN_CODE if shutdown_flag.is_set() else 0
        print(f"[🛑] listener.py 종료 (code={exit_code})")
        shared_result[0] = exit_code
        sys.exit(exit_code)  # os._exit() 대신 sys.exit() 사용

if __name__ == "__main__":
    main()
'''
    file_path = vscode_path / "listener.py"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(listener_content)
    print("✅ listener.py 생성 완료")
    

def _modify_sam_template_yaml(template_file_path: Path):
    """Modifies the SAM template.yaml file to include RequestParameters."""
    if not template_file_path.is_file():
        print(f"❌ template.yaml 파일을 찾을 수 없습니다: {template_file_path}")
        return

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
                    new_lines.append(f"{indent_base}RequestParameters:\n")
                    new_lines.append(f"{indent_param_item}- method.request.querystring.reinvoked\n")
                    inserted = True
        
        if inserted:
            with open(template_file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"✅ template.yaml 수정 완료: RequestParameters 추가")
        else:
            print(f"⚠️ template.yaml 수정 실패: '{target_line_content}' 라인을 찾지 못했습니다. 파일 내용을 확인해주세요.")
    
    except Exception as e:
        print(f"❌ template.yaml 수정 중 오류 발생: {e}")

def _add_package_to_requirements(requirements_file_path: Path, package_name: str):
    """Appends a package to the requirements.txt file if not already present."""
    try:
        # Ensure the parent directory exists
        requirements_file_path.parent.mkdir(parents=True, exist_ok=True)

        line_to_add = f"{package_name}\n"
        
        if requirements_file_path.is_file():
            with open(requirements_file_path, "r+", encoding="utf-8") as f:
                lines = f.readlines()
                # Check if package (with or without newline) is already in the file
                package_exists = any(package_name == line.strip() for line in lines)
                
                if not package_exists:
                    # Ensure the file ends with a newline before appending
                    if lines and not lines[-1].endswith('\n'):
                        f.write('\n')
                    f.write(line_to_add)
                    print(f"✅ '{package_name}' 추가 완료: {requirements_file_path}")
                else:
                    print(f"ℹ️ '{package_name}' 이미 존재함: {requirements_file_path}")
        else:
            # If requirements.txt doesn't exist, create it and add the package
            with open(requirements_file_path, "w", encoding="utf-8") as f:
                f.write(line_to_add)
            print(f"✅ '{package_name}' 추가 완료 (requirements.txt 새로 생성): {requirements_file_path}")

    except Exception as e:
        print(f"❌ {requirements_file_path} 파일 수정 중 오류 발생: {e}")

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
                "--name", project_name,
                "--no-interactive",
                "--runtime", "python3.13",
                "--dependency-manager", "pip",
                "--app-template", "hello-world"
            ], check=True, cwd=Path.cwd()) # Ensure sam init runs in the current working directory
            print(f"✅ SAM 프로젝트 자동 생성 완료")

            # template.yaml 수정 시작
            template_file_path = Path.cwd() / project_name / "template.yaml"
            _modify_sam_template_yaml(template_file_path) # MODIFIED
            # template.yaml 수정 종료
            
            # Path.cwd() / "hello_world" / requirements.txt 파일에 buggerking 패키지 추가
            requirements_file_path = Path.cwd() / project_name / "hello_world" / "requirements.txt"
            _add_package_to_requirements(requirements_file_path, "buggerking")
            
            print(f"ℹ️ 터미널에서 다음 명령을 실행하여 디렉토리를 변경하세요: cd {project_name}")

        except subprocess.CalledProcessError as e:
            print(f"❌ SAM 프로젝트 생성 실패: {e}")
        except Exception as e: # Catch other potential errors during the process
            print(f"❌ SAM 템플릿 처리 중 예기치 않은 오류 발생: {e}")
    else:
        print("🛠️ SAM CLI 인터랙티브 모드를 실행합니다.")
        try:
            subprocess.run(["sam", "init"], check=True)
            print("✅ SAM 프로젝트 수동 생성 완료")
            print("ℹ️ 수동 모드에서는 SAM 프로젝트가 생성된 후, 해당 디렉토리로 직접 이동해주세요.")
            print("   프로젝트 이름은 'sam init' 실행 시 직접 입력한 값입니다.")
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

    try:
        # launch.json 생성
        create_launch_json(port)
        
        # tasks.json 생성
        create_tasks_json()
        
        # loop_controller.py 파일 생성
        # create_loop_controller()
        
        # listener.py 파일 생성
        # create_listener()

        # 방화벽 규칙 추가
        add_firewall_rule(port)

        # sam init 실행 방식 선택
        sam_mode = input("SAM 프로젝트를 자동 생성할까요? (Y/n): ").strip().lower()
        auto_mode = sam_mode != 'n'

        create_sam_template(auto_mode=auto_mode)

        print("🎉 buggerking init 완료!")

    except Exception as e:
        print(f"❌ buggerking 초기 설정 중 오류가 발생했습니다: {e}")
