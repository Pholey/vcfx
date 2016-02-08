# -*- coding: utf-8 -*-
import io
from .fields import getField, Unknown
from pydash.collections import filter_ as ifilter, partition, map_ as imap
from itertools import takewhile

def parseline(line):
    segs = line.split(":")

    # We could be in a multi-line value
    if len(segs) == 1:
        return None

    descriptors = segs[0].split(";")

    # No attributes with this field
    value = segs[1]

    # Seperate our field attributes from their name
    keys, attrs = partition(descriptors, lambda x: "=" not in x)
    key = keys[0]

    # Check for the existance of a subkey:
    subkey = None
    if "." in key:
        subkey, key = key.split(".")

    def normalizeAttr(item):
        key, value = item.split("=")
        return {key: value}

    attrs = imap(attrs, normalizeAttr)

    return subkey, key, attrs, value


class Reader(object):
    def __init__(self, fpath=None):
        super(Reader, self).__init__()
        self.fpath = fpath

        if fpath == None or type(fpath) != str:
            raise ValueError("A valid filepath must be provided")

        self.handle = io.open(self.fpath, "r", encoding="utf-8", newline="\r\n")

        # A "virtual" AST, Doesn't store any data from the vcard,
        # just metadata (i.e lineno)
        self._vAST = list(self._discover_nodes())

        self.positions = {
            "address":      self._get_node_positions("ADR"),
            "altbirthday":  self._get_node_position("X-ALTBDAY"),
            "begin":        self._get_node_position("BEGIN", required=True),
            "birthday":     self._get_node_position("BDAY"),
            "email":        self._get_node_positions("EMAIL"),
            "end":          self._get_node_position("END", required=True),
            "fullname":     self._get_node_position("FN"),
            "label":        self._get_node_positions("X-ABLabel"),
            "name":         self._get_node_position("N"),
            "organization": self._get_node_position("ORG"),
            "photo":        self._get_photo_range(),
            "prodid":       self._get_node_position("PRODID"),
            "telephone":    self._get_node_positions("TEL"),
            "url":          self._get_node_positions("URL"),
            "version":      self._get_node_position("VERSION"),
        }

    def _filter_nodes(self, fn):
        return ifilter(self._vAST, fn)

    def find_nodes_by_key(self, key):
        return self._filter_nodes(lambda n: n.KEY == key)

    def find_nodes_by_subkey(self, subkey):
        return self._filter_nodes(lambda n: n.subkey == subkey)

    def _flatten_labels(self):
        label_idxs = self.positions["label"]

        if label_idxs == None:
            return

        label_nodes = [self._vAST[x] for x in label_idxs]

        for node in label_nodes:
            subkey = node.subkey
            print(subkey)

            # Find the parent node to attach our label
            # TODO(cassidy): This could break if there can be more than 2 items
            #                with the same subkey, research
            parent = self._filter_nodes(lambda n: n.subkey == subkey)[0]

            print(parent)

    def _get_node_position(self, key, required=False):
        q = self.find_nodes_by_key(key)

        if len(q) == 0 and required:
            raise ValueError("Could not determine vcard version")
        elif len(q) == 0:
            return None

        return q[0].lineno

    def _get_node_positions(self, key, required=False):
        q = self.find_nodes_by_key(key)

        if len(q) == 0 and required:
            raise ValueError("Could not determine vcard version")
        elif len(q) == 0:
            return None

        return [x.lineno for x in q]

    def _get_photo_range(self):
        """Attempts to discover where the photo attribute starts and ends"""

        # Do we have a photo?
        photo = self.find_nodes_by_key("PHOTO")

        if len(photo) == 0:
            return None

        # Grab where our photo starts in our vAST
        start_idx = self._vAST.index(photo[0])
        vAST_slice = self._vAST[start_idx:]

        def inPhotoSince(start):
            def wrapped(a):
                if type(a) == type(start) or type(a) == Unknown:
                    return True
                else:
                    return False
            return wrapped

        # Take every item in our vAST from the photo declaration
        # to the last UNKNOWN token
        photo_slice = list(takewhile(inPhotoSince(photo[0]), vAST_slice))
        start_line, end_line = photo_slice[0].lineno, photo_slice[-1].lineno

        return {"start": start_line, "end": end_line}

    def _discover_nodes(self):
        """ Cycle through our fields and record their positions for later
            retrieval
        """
        lineno = 0
        for line in self.readlines():
            parsed = parseline(line)

            if (parsed != None):
                subkey, key, attrs, value = parseline(line)
                print(subkey, key, attrs)
                t = getField(key)

                if t == None:
                    # We don't know what it is, process it later
                    t = Unknown(lineno=lineno)
                else:
                    t = t(subkey=subkey, lineno=lineno)

                yield t
            else:
                yield Unknown(lineno=lineno)

            lineno += 1

        # Return us to the beginning of the file
        self.handle.seek(0)

    def _read_line_numbers(self, l=[]):
        lineno = 0
        for line in self.readlines():
            if lineno in l:
                yield line

            lineno += 1

        self.handle.seek(0)

    def _read_line_range(self, start, end):
        r = list(range(start, end + 1))
        yield from self._read_line_numbers(r)

    def readlines(self, start=0, end=0):
        yield from self.handle

    def filterlines(self, fn=bool):
        for line in readlines(self):
            if fn(line):
                yield line
