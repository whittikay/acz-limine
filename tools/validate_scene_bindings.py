#!/usr/bin/env python3
"""Cross-check SWG texture descriptor tables against the enclosing SWAD TIM2s.
Observed layout: SWG+0x64 descriptor offset, +0x68 count; 12 bytes per entry:
uint32 texture index, uint16 width/height, uint32 unknown flag. Not a timeline decoder.
"""
import csv
import json
import struct
from pac_extract import ROOT


def main():
    resources=list(csv.DictReader((ROOT/'analysis/swad_manifest.csv').open()))
    textures={r['name']:r for r in json.loads((ROOT/'analysis/decoded_manifest.json').read_text())}
    cache={};bindings=[];scenes=0
    for i,scene in enumerate(resources):
        if scene['detected_type']!='SWG scene':continue
        entry=int(scene['entry'])
        if entry not in cache:cache[entry]=(ROOT/f'assets/pac/{entry:04d}.dat').read_bytes()
        b=cache[entry];base=int(scene['relative_offset']);size=int(scene['size'])
        table,count=struct.unpack_from('<II',b,base+0x64)
        if table+12*count>size:raise ValueError('Descriptor table out of bounds')
        following=[]
        for r in resources[i+1:]:
            if r['entry']!=scene['entry'] or r['swad_offset']!=scene['swad_offset'] or r['detected_type']=='SWG scene':break
            if r['detected_type']=='TIM2 texture':following.append(r)
        if count!=len(following):raise ValueError(f'{scene["scene"]}: descriptor count != TIM2 count')
        for index,r in enumerate(following):
            tex_index,w,h,flag=struct.unpack_from('<IHHI',b,base+table+12*index)
            t=textures[r['texture_name']]
            if tex_index!=index or not (0<w<=t['width'] and 0<h<=t['height']):
                raise ValueError(f'SWG/TIM2 descriptor mismatch: {scene["scene"]} {index}: {(tex_index,w,h)} vs {(index,t["width"],t["height"])}')
            bindings.append(dict(entry=entry,scene=scene['scene'],swg_offset=base,texture_index=tex_index,
                                 texture_name=r['texture_name'],logical_width=w,logical_height=h,
                                 stored_width=t['width'],stored_height=t['height'],unknown_flag=flag))
        scenes+=1
    with (ROOT/'analysis/scene_texture_bindings.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(bindings[0]));w.writeheader();w.writerows(bindings)
    print(f'Cross-validated {len(bindings)} SWG texture bindings in {scenes} scenes')
    for r in bindings:
        if r['texture_name'] in ('1239_00163d60','1238_000869e0'):print(r)


if __name__=='__main__':main()
