import argparse
import os
import platform
import signal
import sys
import traceback

import yaml

import state_machine_operator
import state_machine_operator.defaults as defaults
from state_machine_operator.client import get_subparser_helper
from state_machine_operator.config import load_config, load_workflow_config

from .manager import WorkflowManager


def get_parser():
    parser = argparse.ArgumentParser(
        description="State Machine Operator Manager",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--debug",
        help="logger debug mode",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--quiet",
        help="quiet mode",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--version",
        help="show software version.",
        default=False,
        action="store_true",
    )
    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        dest="command",
    )
    subparsers.add_parser("version", description="show software version")
    start = subparsers.add_parser(
        "start",
        description="start the workflow manager",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    start.add_argument(
        "--manager-config",
        dest="manager_config",
        help="Workflow manager config filename",
        default="wfmanager.yaml",
    )
    start.add_argument(
        "--scheduler",
        help="Scheduler to use (defaults to Kubernetes)",
        choices=defaults.supported_schedulers,
        default="kubernetes",
    )
    start.add_argument(
        "config",
        help="Workflow config (required)",
    )
    start.add_argument(
        "--config-dir",
        help="Directory with configuration files.",
    )
    return parser


def main():
    parser = get_parser()

    def help(return_code=0):
        version = state_machine_operator.__version__

        print("\nState Machine Operator Manager v%s" % version)
        parser.print_help()
        sys.exit(return_code)

    # If the user didn't provide any arguments, show the full help
    if len(sys.argv) == 1:
        help()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    # Show the version and exit
    if args.command == "version" or args.version:
        print(state_machine_operator.__version__)
        sys.exit(0)

    # retrieve subparser (with help) from parser
    # This is not currently used and can be removed
    get_subparser_helper(args, parser)

    # Load workflow manager config
    wfconfig = load_config(args.config_dir, args.manager_config)
    print(wfconfig)

    # This is the workflow config that defines files for jobs
    workflow = load_workflow_config(args.config, args.config_dir, debug=args.debug)

    # Create the workflow manager
    print(f"> Launching workflow manager on ({platform.node()})")
    manager = WorkflowManager(wfconfig, scheduler=args.scheduler, workflow=workflow)
    manager.start()

if __name__ == "__main__":
    main()
