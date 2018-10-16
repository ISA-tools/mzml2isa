# coding: utf-8
import os
import sys

# Patch the PYTHONPATH to use the local mzml2isa package
proj = os.path.abspath(os.path.join(__file__, "..", ".."))
sys.path.insert(0, os.path.join(proj, "mzml2isa"))
