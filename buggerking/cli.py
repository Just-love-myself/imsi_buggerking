import argparse
from .init import init

def main():
    parser = argparse.ArgumentParser(prog='buggerking')
    subparsers = parser.add_subparsers(dest='command')

    # buggerking init
    subparsers.add_parser('init', help='Initialize buggerking')

    args = parser.parse_args()
    
    if args.command == 'init':
       init.init()