import json, os, tempfile
from backend.services import pipeline

code = 'void f(char *s){ char buf[8]; strcpy(buf, s); }\n'   # obvious overflow
with tempfile.NamedTemporaryFile('w', suffix='.c', delete=False) as f:
    f.write(code); p = f.name
r = pipeline.scan_file(p)
os.unlink(p)
print(type(r))
print(json.dumps(r, indent=2, default=str)[:3000])