#!/usr/bin/env python3
"""Create honest, non-AI wallpaper derivatives from recovered clean background layers.
No scene reconstruction or speculative layer blending. Originals remain separate.
"""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageFilter, PngImagePlugin
from pac_extract import ROOT
from decode_tim2 import contact_sheet

SOURCES=[
    ('acz-main-menu-base','1239_00163d60','MainSelect background underlay (not the full animated scene)'),
    ('acz-title-red-clouds','1238_000869e0','Title-screen red clouds underlay (not the selection-menu scene)'),
]


def save_png(im,path,description):
    info=PngImagePlugin.PngInfo()
    info.add_text('Description',description)
    info.add_text('Software','Pillow; Gaussian prefilter + Lanczos; no generative processing')
    im.save(path,pnginfo=info,compress_level=9)


def contrast_white(im):
    rgb=np.asarray(im,dtype=np.float64)/255
    linear=np.where(rgb<=0.04045,rgb/12.92,((rgb+0.055)/1.055)**2.4)
    luminance=linear@np.array([0.2126,0.7152,0.0722])
    return float((1.05/(luminance+0.05)).min())


def main():
    originals=ROOT/'artwork/original';originals.mkdir(parents=True,exist_ok=True)
    walls=ROOT/'wallpapers';walls.mkdir(exist_ok=True)
    manifest=[];comparisons=[]
    records={r['name']:r for r in json.loads((ROOT/'analysis/decoded_manifest.json').read_text())}
    for basename,name,description in SOURCES:
        r=records[name]
        for suffix,new_suffix in [('.tm2','.tm2'),('.png','-512x448.png'),('_raw-alpha.png','-512x448-raw-gs-alpha.png'),('_indices.png','-indices.png')]:
            shutil.copyfile(ROOT/f'assets/tim2/{name}{suffix}',originals/f'{basename}{new_suffix}')
        blob=(originals/f'{basename}.tm2').read_bytes()
        start=16+r['header_size']+r['image_size']
        (originals/f'{basename}-palette-rgba.bin').write_bytes(blob[start:start+r['clut_size']])
        im=Image.open(originals/f'{basename}-512x448.png').convert('RGBA')
        if im.getextrema()[3]!=(255,255):raise ValueError('Expected an opaque base layer')
        im=im.convert('RGB')
        for label,blur in [('',0.65),('-unfiltered',0.0)]:
            source=im.filter(ImageFilter.GaussianBlur(blur)) if blur else im
            # Interpret PS2's 512x448 sample grid as a 4:3 display (PAR 7:6).
            # Upscale to 3840x2880 then center crop to 16:9; no stretching to 16:9.
            scaled=source.resize((3840,2880),Image.Resampling.LANCZOS)
            result=scaled.crop((0,360,3840,2520))
            desc=f'{description}. Source {name}, native 512x448. 4:3 aspect correction; center crop to 16:9; prefilter sigma/radius {blur} source pixels; Lanczos. Not a captured/reconstructed game frame.'
            dest=walls/f'{basename}-3840x2160{label}.png'
            save_png(result,dest,desc)
            with Image.open(dest) as check:
                check.load()
                if check.size!=(3840,2160) or check.mode!='RGB':raise ValueError('Wallpaper verification failed')
            manifest.append(dict(path=str(dest.relative_to(ROOT)),source=name,description=description,
                                 source_entry=r['entry'],source_relative_offset=r['relative_offset'],
                                 source_pac_offset=r['offset'],source_tm2_sha256=r['tm2_sha256'],
                                 native_size=[512,448],size=[3840,2160],mode='RGB',prefilter_radius=blur,
                                 resize_before_crop=[3840,2880],crop_box=[0,360,3840,2520],
                                 equivalent_source_crop=[0,56,512,392],
                                 minimum_white_text_contrast=contrast_white(result),
                                 sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
            if not label:
                preview=ROOT/f'previews/{basename}-960x540.png'
                result.resize((960,540),Image.Resampling.LANCZOS).save(preview)
                comparisons.append((preview,basename+' / clean 4K derivative'))
    contact_sheet(comparisons,ROOT/'previews/wallpaper_comparison.jpg',1,(968,584),'Recovered backgrounds: main menu vs title screen (different scenes)')
    candidates=[('1239_00163d60','MainSelect: red/orange base'),
                ('1239_0012ada0','MainSelect: separate light/particle layer'),
                ('1239_000f2940','MainSelect: separate blue image layer'),
                ('1238_000869e0','Title: red cloud base'),
                ('1238_00032800','Title: separate gold cloud / alpha layer 1'),
                ('1238_0004e8a0','Title: separate gold cloud / alpha layer 2'),
                ('1238_0006a940','Title: separate gold cloud / alpha layer 3'),
                ('1238_00029b00','Title: separate light/particle atlas'),
                ('1238_000a2a80','Title: separate game logo (NOT baked into base)')]
    contact_sheet([(ROOT/f'assets/tim2/{n}.png',f'{n}\n{label}') for n,label in candidates],ROOT/'previews/background_candidates.jpg',3,(360,332),'Candidate layers at native pixel aspect; transparency shown over black')
    (ROOT/'analysis/wallpaper_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for r in manifest:print(r['path'],f"white-text contrast >= {r['minimum_white_text_contrast']:.2f}:1")


if __name__=='__main__':main()
