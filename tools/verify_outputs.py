#!/usr/bin/env python3
"""End-to-end local integrity verification; all archive handles are read-only."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from decode_tim2 import decode
from pac_extract import ROOT


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    expected=json.loads((ROOT/'analysis/source-sha256.json').read_text())
    actual={name:sha256(ROOT/name) for name in expected}
    if expected!=actual:raise ValueError('Original input file changed!')
    entries=json.loads((ROOT/'assets/pac/extraction_manifest.json').read_text())
    textures=json.loads((ROOT/'analysis/decoded_manifest.json').read_text())
    with (ROOT/'DATA.PAC').open('rb') as pac:
        for r in entries:
            path=ROOT/f'assets/pac/{r["index"]:04d}.dat'
            if path.stat().st_size!=r['size'] or sha256(path)!=r['sha256']:raise ValueError('DAT hash mismatch')
            pac.seek(r['offset']);source=pac.read(r['size'])
            if source!=path.read_bytes():raise ValueError('DAT differs from original PAC bytes')
        for r in textures:
            path=ROOT/f'assets/tim2/{r["name"]}.tm2'
            blob=path.read_bytes()
            if hashlib.sha256(blob).hexdigest()!=r['tm2_sha256']:raise ValueError('TM2 hash mismatch')
            pac.seek(r['offset'])
            if pac.read(len(blob))!=blob:raise ValueError('TM2 differs from PAC slice')
            indices,rgba,display=decode(blob,r)
            for suffix,expected_pixels in [('_raw-alpha.png',rgba),('.png',display),('_indices.png',indices)]:
                if expected_pixels is not None:
                    with Image.open(ROOT/f'assets/tim2/{r["name"]}{suffix}') as im:
                        if not np.array_equal(np.asarray(im),expected_pixels):raise ValueError('Decoded PNG mismatch')
    wallpapers=json.loads((ROOT/'analysis/wallpaper_manifest.json').read_text())
    layered_path=ROOT/'analysis/reference/layered_manifest.json'
    reference_verified=False
    if layered_path.exists():
        layered=json.loads(layered_path.read_text())
        if sha256(ROOT/layered['reference'])!=layered['reference_sha256']:
            raise ValueError('Reference screenshot changed')
        if sha256(ROOT/layered['native_artwork'])!=layered['native_sha256']:
            raise ValueError('Layered native artwork changed')
        for path,digest in layered['sources_sha256'].items():
            if sha256(ROOT/path)!=digest:raise ValueError('Layer source changed')
        wallpapers.extend(layered['wallpapers'])
        reference_verified=True
    for r in wallpapers:
        path=ROOT/r['path']
        if sha256(path)!=r['sha256']:raise ValueError('Wallpaper hash mismatch')
        with Image.open(path) as im:
            im.load()
            if im.size!=(3840,2160) or im.mode!='RGB':raise ValueError('Wallpaper dimensions/mode mismatch')
    result=dict(original_inputs_unchanged=True,original_sha256=actual,
                extracted_dat_files_verified=len(entries),dat_bytes_verified=sum(r['size'] for r in entries),
                original_tm2_slices_verified=len(textures),decoded_pngs_verified=sum(2+(r['image_type'] in (4,5)) for r in textures),
                wallpapers_verified=len(wallpapers),wallpaper_dimensions=[3840,2160],
                reference_screenshot_unchanged=reference_verified)
    (ROOT/'analysis/verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
