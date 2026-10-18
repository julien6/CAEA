"""Recover ALL archived results after worker success and post-archive cleanup failure.

This never calls a model, invents a metric or relabels the original Slurm state.
Acceptance additionally requires a complete recorded-response replay in the job.
"""
import argparse,json,hashlib,shutil,itertools,subprocess
from pathlib import Path
from caea.org_v2.staging import materialize
from caea.org_v2.storage import episode_files,read_episode
from caea.org_v2.model import digest
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
cfg=json.loads(Path(a.config).read_text());root=Path(a.root);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
(out/'episodes').mkdir();(out/'cases').mkdir();seen=set();all_seeds=set();provenance=[]
with (out/'llm_calls.jsonl').open('wb') as combined:
 for parent in cfg['recovery_parents']:
    name=parent['run'];base=root/name;pcfg=json.loads((base/'config.json').read_text())
    assert (base/'outputs'/'worker_exit.txt').read_text().strip()=='0','scientific worker did not succeed'
    error=(base/'outputs'/f"slurm-{parent['job_id']}.err").read_text()
    assert 'rm: cannot remove' in error and 'Directory not empty' in error and 'Traceback' not in error
    state=(out/'parent_accounting.tsv').read_text()
    assert any(line.split('|')[:3]==[str(parent['job_id']),'FAILED','1:0'] for line in state.splitlines())
    for key in ('settings','organizations','policies','policy_seeds','llm'):assert pcfg[key]==cfg[key]
    assert not (all_seeds & set(pcfg['case_seeds']));all_seeds.update(pcfg['case_seeds'])
    folder=materialize(root,name);meta=json.loads((folder/'metadata.json').read_text())
    assert meta['config_sha256']==digest(pcfg) and meta['finished']>0
    expected={f"{s['name']}-{seed}-{ps}-{org}-{policy}" for s,seed,ps,org,policy in itertools.product(pcfg['settings'],pcfg['case_seeds'],pcfg['policy_seeds'],pcfg['organizations'],pcfg['policies'])}
    paths=episode_files(folder);records=[read_episode(path) for path in paths]
    assert {r['id'] for r in records}==expected and len(records)==96
    assert not (seen & expected);seen.update(expected)
    for path in paths:shutil.copyfile(path,out/'episodes'/path.name)
    for path in (folder/'cases').glob('*.json'):
        assert not (out/'cases'/path.name).exists();shutil.copyfile(path,out/'cases'/path.name)
    raw=(folder/'llm_calls.jsonl').read_bytes();calls=[json.loads(line) for line in raw.splitlines()]
    assert sum('request' in r for r in calls)==meta['llm']['calls']
    assert {r['episode'] for r in calls}<=expected
    combined.write(raw)
    dest=out/'parents'/name;dest.mkdir(parents=True)
    for item in ('metadata.json','used_config.json','loaded-model.txt','models.json','image-sha256.txt','pip-freeze.txt','model-verification.json','nvidia-smi.txt'):
        if (folder/item).exists():shutil.copyfile(folder/item,dest/item)
    archive=base/'outputs'/'artifacts.tar.gz'
    provenance.append({**parent,'original_slurm_state':'FAILED','worker_exit':0,'failure_phase':'post-archive NFS directory cleanup','episodes':len(records),'archive_sha256':hashlib.file_digest(archive.open('rb'),'sha256').hexdigest(),'all_inner_hashes_verified':True,'new_inference_calls':0,'original_metadata':meta})
assert all_seeds==set(cfg['case_seeds']) and len(seen)==192
(out/'used_config.json').write_text(json.dumps(cfg,indent=2))
(out/'recovery.json').write_text(json.dumps({'parents':provenance,'episodes':192,'new_inference_calls':0,'acceptance':'Full deterministic replay additionally required; original failures remain in accounting.'},indent=2))
# Present the intact recovered bundle to the existing replay interface.
staged=Path('recovery-root')/'org-final-synthetic-recovered';staged.mkdir(parents=True)
(staged/'config.json').write_text(json.dumps(cfg));(staged/'outputs').symlink_to(out.resolve(),target_is_directory=True)
print('Recovered all 192 archived episodes; replay required',flush=True)
