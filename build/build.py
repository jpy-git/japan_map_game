#!/usr/bin/env python3
"""Inject the map data from paths.json into game.template.html -> ../index.html"""
import json, os, re
here = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(here, 'game.template.html')).read()
d = json.load(open(os.path.join(here, 'paths.json')))
ins = d['inset']
for k, v in [('__W__', d['w']), ('__H__', d['h']),
             ('__IX__', ins['x']), ('__IY__', ins['y']),
             ('__IW__', ins['w']), ('__IH__', ins['h']),
             ('__ILX__', round(ins['x'] + 9, 1)), ('__ILY__', round(ins['y'] + ins['h'] - 10, 1))]:
    t = t.replace(k, str(v))
t = t.replace('__DATA__', json.dumps({'prefs': d['prefs']}, ensure_ascii=False, separators=(',', ':')))
left = re.findall(r'__[A-Z]+__', t)
assert not left, 'unfilled placeholders: %s' % left
out = os.path.join(here, '..', 'index.html')
open(out, 'w').write(t)
print('wrote index.html (%d bytes)' % len(t))
