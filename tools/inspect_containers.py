#!/usr/bin/env python3
"""Validate SWAD offset/size tables and associate TIM2s with preceding SWG scenes.
All classifications are signature-based; this does NOT interpret SWG timelines.
"""
from pathlib import Path
import csv
import hashlib
import json
import struct
import subprocess
from collections import Counter
from pac_extract import ROOT, sub_offsets


def main():
    decoded=json.loads((ROOT/'analysis/decoded_manifest.json').read_text())
    known={r['name']:r for r in decoded}
    inventory=list(csv.DictReader((ROOT/'analysis/inventory.csv').open()))
    manifests=[]
    for path in sorted((ROOT/'assets/pac').glob('*.dat')):
        entry=int(path.stem);b=path.read_bytes()
        tops=sub_offsets(b,0,len(b))
        if tops is None:raise ValueError(f'Invalid top-level directory: {path}')
        scenes=[];signatures=Counter()
        for j,base in enumerate(tops):
            limit=tops[j+1] if j+1<len(tops) else len(b)
            magic=b[base:base+4]
            signatures[magic.hex()]+=1
            if magic!=b'SWAD':continue
            n=struct.unpack_from('<I',b,base+4)[0]
            if not 0<n<10000 or base+8+n*8>limit:raise ValueError('Invalid SWAD count')
            last=8+n*8;scene=''
            for k in range(n):
                off,size=struct.unpack_from('<II',b,base+8+k*8)
                if not size or off<last or base+off+size>limit:raise ValueError('SWAD overlap/out of bounds')
                last=off+size
                pos=base+off;signature=b[pos:pos+4]
                if signature==b'SWG\0':
                    scene=b[pos+8:pos+72].split(b'\0')[0].decode('ascii')
                    scenes.append(scene)
                name=f'{entry:04d}_{pos:08x}' if signature==b'TIM2' else ''
                if name and name not in known:raise ValueError('SWAD TIM2 missing from scanner')
                if name and size!=known[name]['total_size']+16:raise ValueError('SWAD/TIM2 size mismatch')
                manifests.append(dict(entry=entry,swad_offset=base,record=k,relative_offset=pos,size=size,
                                      signature_hex=signature.hex(),detected_type='TIM2 texture' if name else ('SWG scene' if signature==b'SWG\0' else 'unknown'),
                                      scene=scene,texture_name=name,sha256=hashlib.sha256(b[pos:pos+size]).hexdigest()))
        row=inventory[entry]
        row['detected_type']='offset-table container / SWAD UI package / embedded TIM2'
        row['scene_names']=';'.join(scenes)
        row['child_signatures']=json.dumps(signatures,sort_keys=True)
        row['extracted_path']=str(path.relative_to(ROOT))
        row['file_command']=subprocess.check_output(['file','-b',str(path)],text=True).strip()
    for row in inventory:
        for field in ('scene_names','child_signatures','extracted_path','file_command'):row.setdefault(field,'')
    for filename,records in [('inventory_enriched.csv',inventory),('swad_manifest.csv',manifests)]:
        with (ROOT/'analysis'/filename).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    print(f'Validated {len(manifests)} SWAD resources; {sum(r["detected_type"]=="TIM2 texture" for r in manifests)} TIM2 records exactly match scanner sizes')
    for entry in (1237,1238,1239):
        print(entry,inventory[entry]['scene_names'])
        for r in manifests:
            if r['entry']==entry and r['texture_name']:print(r['record'],r['texture_name'],r['size'])


if __name__=='__main__':main()
