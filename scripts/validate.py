#!/usr/bin/env python

import sys
import os
from isatools import isatab


if __name__ == "__main__":
    study_dir = sys.argv[-2]
    config_dir = sys.argv[-1]

    with open(os.path.join(study_dir, 'i_Investigation.txt')) as s:
        status = isatab.validate2(s, config_dir)

    if status['errors']:
        sys.exit("Validation failed !\nErrors:\n{}".format('\n'.join(str(x) for x in status['errors'])))
