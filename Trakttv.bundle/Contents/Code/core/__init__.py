import sys

# Modules???

import plugin
sys.modules['core.plugin'] = plugin

import header
sys.modules['core.header'] = header

import helpers
sys.modules['core.helpers'] = helpers

import eventing
sys.modules['core.eventing'] = eventing

import http
sys.modules['core.http'] = http

import pms
sys.modules['core.pms'] = pms