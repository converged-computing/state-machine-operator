import argparse
import platform
import sys

import state_machine_operator
import state_machine_operator.defaults as defaults
from state_machine_operator.client import get_subparser_helper
from state_machine_operator.config import load_workflow_config

from .manager import WorkflowManager


def get_parser():
    parser = argparse.ArgumentParser(
        description="State Machine Operator Manager",
        formatter_class=argparse.RawTextHelpFormatter,
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
        "--scheduler",
        help="Scheduler to use (defaults to Kubernetes)",
        choices=defaults.supported_schedulers,
        default="kubernetes",
    )
    start.add_argument(
        "config",
        help="Workflow configuration file (required)",
    )
    start.add_argument(
        "--registry",
        help="Workflow registry to push/pull artifacts",
    )
    start.add_argument(
        "--filesystem",
        help="Use local filesystem for output instead.",
        default=False,
        action="store_true",
    )
    start.add_argument(
        "--workdir",
        help="Use this working directory for the workflow (will default to temporary location if not set).",
    )
    start.add_argument(
        "--config-dir",
        help="Directory with configuration files.",
    )
    start.add_argument(
        "--quiet",
        help="Don't print progress",
        default=False,
        action="store_true",
    )
    start.add_argument(
        "--plain-http",
        help="Use plain http for the registry.",
        default=False,
        action="store_true",
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
    args, _ = parser.parse_known_args()

    # Show the version and exit
    if args.command == "version" or args.version:
        print(state_machine_operator.__version__)
        sys.exit(0)

    # retrieve subparser (with help) from parser
    # This is not currently used and can be removed
    get_subparser_helper(args, parser)

    # This is the workflow config that defines files for jobs
    workflow = load_workflow_config(args.config, args.config_dir)

    # Create the workflow manager
    print(f"> Launching workflow manager on ({platform.node()})")
    manager = WorkflowManager(
        workflow,
        scheduler=args.scheduler,
        registry=args.registry,
        filesystem=args.filesystem,
        # Will overwrite what is set in config
        workdir=args.workdir,
        plain_http=args.plain_http,
        quiet=args.quiet,
    )
    manager.start()


if __name__ == "__main__":
    main()
