# cli.py
import argparse


def setup_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--yes', action='store_true', help='Automatically select yes for all prompts')
    parser.add_argument('-n', '--no', action='store_true', help='Automatically select no for all prompts')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Populate with debug content and skip all generation')
    return parser
