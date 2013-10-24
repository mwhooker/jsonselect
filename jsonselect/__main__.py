from .jsonselect import select


def parser():
    import argparse
    parser = argparse.ArgumentParser(description='parse json with jsonselect.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--list', '-l', action='store_true',
                       help="new-line separated list of values. "
                       "works best on lists.")
    group.add_argument('--machine-readable', action='store_true',
                       help="Print json with no formatting")
    parser.add_argument('selector')
    parser.add_argument('infile', nargs="?")
    return parser


def cli():
    import sys
    import json
    parser_ = parser()
    args = parser_.parse_args()

    if args.infile:
        fin = open(args.infile)
    elif sys.stdin:
        fin = sys.stdin
    else:
        parser_.print_help()
        sys.exit(1)

    obj = json.load(fin)
    selection = select(args.selector, obj)
    if not selection:
        sys.exit(2)
    if args.machine_readable:
        print json.dumps(selection)
    elif args.list:
        if hasattr(selection, '__iter__'):
            for i in selection:
                print i
        else:
            print selection
    else:
        print json.dumps(selection, indent=4)

cli()
