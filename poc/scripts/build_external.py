from caea.org_v2.external import prepare
import json
from pathlib import Path
root='/projects/caea/datasets/m57-public-docs'
a=prepare(root,root+'/tasks')
Path('outputs/annotation_audit.json').write_text(json.dumps(a,indent=2))
print('Verified tasks:',len(a))
