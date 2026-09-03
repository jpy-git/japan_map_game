#!/usr/bin/env python3
"""Inject both maps into game.template.html -> ../index.html

paths.json (Japan) predates the two-country layout, so it is reshaped here into
the record the game reads: units keyed by id, plus which unit lives in the inset
box and what to call it. paths_uk.json is already written in that shape.
"""
import json, os, re

here = os.path.dirname(os.path.abspath(__file__))


def load(name):
    return json.load(open(os.path.join(here, name)))


jp = load('paths.json')
jp['units'] = jp.pop('prefs')
jp['insetId'] = 47            # Okinawa
jp['insetLabel'] = '沖縄'

uk = load('paths_uk.json')

t = open(os.path.join(here, 'game.template.html')).read()
for k, d in (('__JP_DATA__', jp), ('__UK_DATA__', uk)):
    t = t.replace(k, json.dumps(d, ensure_ascii=False, separators=(',', ':')))

left = re.findall(r'__[A-Z_]+__', t)
assert not left, 'unfilled placeholders: %s' % left

out = os.path.join(here, '..', 'index.html')
open(out, 'w').write(t)
print('wrote index.html (%d bytes: %d units in Japan, %d in the UK)'
      % (len(t), len(jp['units']), len(uk['units'])))
