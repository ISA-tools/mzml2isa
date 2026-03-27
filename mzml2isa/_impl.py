"""Compatibility helpers for supported Python versions."""

from contextlib import contextmanager
from functools import cache
from functools import cached_property


# --- Available XML parser ---------------------------------------------------
try:
    from lxml import etree

    def get_parent(element, tree):
        """Finds every parent of a tree node.

        Uses the method provided by lxml.etree
        """
        return element.getparent()


except ImportError:

    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

    def get_parent(element, tree):
        """Finds every parent of a tree node.

        As xml.ElementTree has no **.getparent** method, the following was
        proposed here : http://stackoverflow.com/questions/2170610#20132342
        """
        # {c:p for p in tree.iter() for c in p}[element]
        # next(p for p in tree.iter() for c in p if c==element)
        return next(p for p in tree.iter() if element in p)


# --- Available package resources --------------------------------------------

import importlib.resources as importlib_resources
from importlib.resources import files as resource_files


# --- Optional progress bar --------------------------------------------------

try:
    import tqdm
except ImportError:
    tqdm = None


@contextmanager
def pronto_no_multiprocessing():
    """Force pronto to parse ontologies without creating multiprocessing pools."""
    import pronto.utils.pool as pronto_pool

    thread_pool = pronto_pool._ThreadPool
    pronto_pool._ThreadPool = None
    try:
        yield
    finally:
        pronto_pool._ThreadPool = thread_pool


def load_pronto_ontology(pronto_module, filename):
    """Load a pronto ontology, falling back to sequential parsing if needed."""
    try:
        return pronto_module.Ontology(filename)
    except PermissionError:
        with pronto_no_multiprocessing():
            return pronto_module.Ontology(filename)
