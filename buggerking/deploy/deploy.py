# buggerking/deploy.py

import subprocess
import sys
import os
from ..common.common import get_sam_path


def deploy(project_name: str = ".", stack_name: str = "buggerking-stack"):
    """
    AWS SAM 애플리케이션을 배포하는 함수입니다.

    Args:
        project_name (str, optional): 배포할 프로젝트의 경로. 기본값은 현재 디렉토리(".").
        stack_name (str, optional): CloudFormation 스택 이름. 기본값은 "buggerking-stack".

    Raises:
        SystemExit: 프로젝트 디렉토리를 찾을 수 없거나 배포 과정에서 오류가 발생한 경우.

    Note:
        - AWS SAM CLI를 사용하여 애플리케이션을 배포합니다.
        - IAM 권한이 필요한 리소스를 생성할 수 있도록 CAPABILITY_IAM을 사용합니다.
        - S3 버킷을 자동으로 생성하도록 --resolve-s3 옵션을 사용합니다.
    """
    project_path = os.path.abspath(project_name)
    sam_path = get_sam_path()

    project_path = os.path.join(os.getcwd(), project_name)  # 현재 위치에 project_name을 붙여서 경로를 생성

    if not os.path.isdir(project_path):
        print(f"❌ Directory '{project_path}' not found.")
        sys.exit(1)

    try:
        print(f"🚀 Deploying SAM project in '{project_path}'...")

        subprocess.run([
            sam_path,
            "deploy",
            "--stack-name", stack_name,
            "--resolve-s3",
            "--capabilities", "CAPABILITY_IAM",
            "--no-confirm-changeset",
        ], cwd=project_path, check=True)

        print("✅ Deploy completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Deploy failed with error code {e.returncode}")
        sys.exit(e.returncode)
