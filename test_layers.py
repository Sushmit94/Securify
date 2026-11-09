import json, os, tempfile
from backend.services import pipeline

code = 'void f(char *s){ char buf[8]; strcpy(buf, s); }\n'
for suffix in ('.c', '.cpp'):
    with tempfile.NamedTemporaryFile('w', suffix=suffix, delete=False) as f:
        f.write(code); p = f.name
    r = pipeline.scan_file(p)
    os.unlink(p)
    print(suffix, '->', r.get('language'), r.get('tier'), 'layers_run:', r.get('layers_run'), 'findings:', len(r.get('findings', [])))