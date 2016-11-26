import sys
import os

import fs.osfs

# prepare absolute directories
TESTDIR = os.path.dirname(os.path.abspath(__file__))
MAINDIR = os.path.dirname(TESTDIR)
# CONFDIR = os.path.join(TESTDIR, "configs")
# RUNDIR = os.path.join(TESTDIR, "run")

# prepare filesystem
TEST_FS = fs.osfs.OSFS(MAINDIR)

# check if in CI
IN_CI = os.environ.get("CI",'').lower() == "true"

# shortcuts to MTBLS FTP server directories of interest
MTBLS_URLS = {
    'studies':    "/pub/databases/metabolights/studies/public",
    'isacreator': "/pub/databases/metabolights/submissionTool",
}
