import argparse
from .init import init
from .build import build
from .deploy import deploy

def main():
    parser = argparse.ArgumentParser(prog='buggerking')
    subparsers = parser.add_subparsers(dest='command')

    # buggerking init
    subparsers.add_parser('init', help='Initialize buggerking')
    
    # buggerking build
    subparsers.add_parser('build', help='Build the project')
    
    # buggerking deploy
    subparsers.add_parser('deploy', help='Deploy the project')

    args = parser.parse_args()
    
    if args.command == 'init':
       init.init()
    elif args.command == 'build':
        build.build()
    elif args.command == 'deploy':
        deploy.deploy()