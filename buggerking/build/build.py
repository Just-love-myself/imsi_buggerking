import subprocess
import sys
import os

from ..common.common import get_sam_path

def build(project_name: str = ""):
    """
    AWS SAM 애플리케이션을 빌드하는 함수입니다.

    Args:
        project_name (str, optional): 빌드할 프로젝트의 경로. 기본값은 빈 문자열("")로, 현재 디렉토리를 의미합니다.

    Raises:
        SystemExit: 
            - 프로젝트 디렉토리를 찾을 수 없는 경우
            - 빌드 과정에서 오류가 발생한 경우
            - AWS SAM CLI가 설치되어 있지 않은 경우

    Note:
        - AWS SAM CLI를 사용하여 애플리케이션을 빌드합니다.
        - 빌드 과정에서 발생하는 모든 오류를 적절히 처리하고 사용자에게 피드백을 제공합니다.
    """
    sam_path = get_sam_path()
    print(f"🔍 SAM CLI 경로: {sam_path}")

    project_path = os.path.join(os.getcwd(), project_name) # 현재 위치에 project_name을 붙여서 경로를 생성

    if not os.path.isdir(project_path):
        print(f"❌ Project directory '{project_name}' not found.")
        sys.exit(1)

    try:
        print(f"🛠️ Building SAM project in '{project_name}'...")
        subprocess.run([sam_path, "build"], cwd=project_path, check=True)
        print("✅ Build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed with error code {e.returncode}")
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("❌ 'sam' command not found. Make sure AWS SAM CLI is installed.")
        sys.exit(1)
