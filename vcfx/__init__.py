# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals, division
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from .__version__ import __version__, __version_info__  # noqa
from .vcfx import reader

__all__ = ["reader"]
