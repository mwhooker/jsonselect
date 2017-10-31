# jsonselect.py

[![No Maintenance Intended](http://unmaintained.tech/badge.svg)](http://unmaintained.tech/)

[<img src="https://travis-ci.org/mwhooker/jsonselect.png" />](https://travis-ci.org/mwhooker/jsonselect)

jsonselect.py is a python implementation of https://github.com/fd/json_select

You can find more information here http://jsonselect.org/


## Project status

### NO LONGER MAINTAINED

There are plenty of other currently maintained libraries that accomplish the same thing

* http://www.jsoniq.org/
* https://github.com/boto/jmespath
* https://github.com/jmespath/jmespath.py

However, if you submit a concise and tested patch, I will probably merge it in.

jsonselect.py currently implements levels 1 & 2 of these conformance tests https://github.com/lloyd/JSONSelectTests

level 3 is unimplemented because I was having trouble understanding what the correct behavior should be


## Usage

jsonselect can be called directly from the command line.

`python -m jsonselect <selector> < jsonfile`

This is usefull, for example, for parsing out values from JSON APIs.

```sh
$aws ec2 describe-instances --filters "Name=tag:Name,Values=kafka" | python -m jsonselect .InstanceId
["i-12345678", "i-23456789", "i-3456789A"]
```

### Full Usage

```
usage: __main__.py [-h] [--list | --machine-readable] selector [infile]

parse json with jsonselect.

positional arguments:
  selector
  infile

optional arguments:
  -h, --help          show this help message and exit
  --list, -l          new-line separated list of values. works best on lists.
  --machine-readable  Print json with no formatting
```

##Tests

get the upstream conformance tests:
git submodule update --init

Run specific level conformance tests with
nosetests -m '.*_level_1' ./tests/test_conformance.py
