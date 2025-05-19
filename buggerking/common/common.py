import os
import shutil


def find_sam_executable() -> str | None:
    # 1. which로 탐색
    path = shutil.which("sam.cmd") or shutil.which("sam.exe") or shutil.which("sam")
    if path:
        return path

    # 2. 기본 설치 위치 수동 확인
    common_paths = [
        r"C:\Program Files\Amazon\AWSSAMCLI\bin\sam.cmd",
        r"C:\Program Files\Amazon\AWSSAMCLI\bin\sam.exe"
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    return None

def prompt_for_sam_install():
    print("\n❌ AWS SAM CLI가 설치되어 있지 않거나 찾을 수 없습니다.")
    print("📦 설치 안내: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html")
    input("🛠 설치를 완료한 후, Enter를 눌러 계속하세요...")

def get_sam_path() -> str:
    sam_path = find_sam_executable()
    if sam_path:
        return sam_path

    prompt_for_sam_install()

    # 설치 후 다시 탐색 시도
    sam_path = find_sam_executable()
    if sam_path:
        return sam_path

    # 그래도 못 찾으면 사용자에게 경로 직접 입력받기 -> 무한 루프에 빠질 수 있음
    print("📂 SAM 실행 파일 경로를 직접 입력해주세요. (예: C:\\Program Files\\Amazon\\AWSSAMCLI\\bin\\sam.cmd)")
    while True:
        manual_path = input("SAM 경로: ").strip('"')
        if os.path.exists(manual_path):
            return manual_path
        print("❌ 해당 경로에 파일이 존재하지 않습니다. 다시 입력해주세요.")