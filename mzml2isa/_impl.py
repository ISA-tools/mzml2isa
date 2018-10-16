"""Conditional imports of optional dependencies.
"""

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


# --- Optional progress bar --------------------------------------------------

try:
    import tqdm
except ImportError:
    tqdm = None
