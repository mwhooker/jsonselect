from .jsonselect import select


def cli():
    import sys
    import json
    selector = sys.argv[1]
    obj = json.load(sys.stdin)
    print json.dumps(select(selector, obj))

cli()
