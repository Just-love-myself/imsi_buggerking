import argparse
from .init import init
from .build import build
from .deploy import deploy

def main():
    parser = argparse.ArgumentParser(prog='buggerking')
    subparsers = parser.add_subparsers(dest='command')

    # buggerking init
    subparsers.add_parser('init', help='Initialize buggerking')

    args = parser.parse_args()
    
    if args.command == 'init':
       init.init()
    elif args.command == 'build':
        build.build()
    elif args.command == 'deploy':
        deploy.deploy()