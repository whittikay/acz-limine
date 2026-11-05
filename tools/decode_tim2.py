#!/usr/bin/env python3
"""Conservative decoder for the single-picture indexed TIM2s found in this PAC.
Retains byte-exact TM2, index plane, raw palette/GS alpha in PNG, and display PNG.
No swizzle is applied to image data; these assets prove to be linear scanlines.
8-bit CSM1 palettes exchange index bits 3 and 4. GS display alpha = min(255,2*a).
Unsupported cases fail explicitly rather than silently producing guessed artwork.
"""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pac_extract import ROOT


def decode(blob, r):
    if r['pictures'] != 1 or r['mipmaps'] != 1 or r['alignment'] != 0:
        raise ValueError('Only single-picture, single-level, 16-byte aligned TIM2 is supported')
    w,h=r['width'],r['height']
    pixels=blob[16+r['header_size']:16+r['header_size']+r['image_size']]
    n=w*h
    if r['image_type']==4:
        packed=np.frombuffer(pixels,dtype=np.uint8)
        indices=np.empty(len(packed)*2,dtype=np.uint8)
        indices[::2]=packed & 15
        indices[1::2]=packed >> 4
    elif r['image_type']==5:
        indices=np.frombuffer(pixels,dtype=np.uint8)
    elif r['image_type']==3 and len(pixels)==n*4:
        rgba=np.frombuffer(pixels,dtype=np.uint8).reshape(h,w,4).copy()
        display=rgba.copy()
        display[:,:,3]=np.minimum(255,rgba[:,:,3].astype(np.uint16)*2).astype(np.uint8)
        return None,rgba,display
    else:
        raise ValueError(f'Unsupported image type/size: {r["image_type"]}')
    if len(indices)<n:
        raise ValueError('Truncated index plane')
    indices=indices[:n].reshape(h,w)
    cstart=16+r['header_size']+r['image_size']
    clut=blob[cstart:cstart+r['clut_size']]
    if not clut:
        return indices,None,None
    if r['clut_type'] & 0x3f != 3 or len(clut) != r['clut_colors']*4:
        raise ValueError('Unsupported CLUT format')
    palette=np.frombuffer(clut,dtype=np.uint8).reshape(-1,4).copy()
    if r['image_type']==5 and not r['clut_type'] & 0x80:
        order=np.arange(len(palette))
        order=(order & ~24) | ((order & 8)<<1) | ((order & 16)>>1)
        palette=palette[order]
    if int(indices.max())>=len(palette):
        raise ValueError('Palette index out of range')
    rgba=palette[indices]
    display=rgba.copy()
    display[:,:,3]=np.minimum(255,rgba[:,:,3].astype(np.uint16)*2).astype(np.uint8)
    return indices,rgba,display


def contact_sheet(items, path, columns=5, cell=(224,224), title=''):
    cw,ch=cell
    font=ImageFont.truetype('/usr/share/fonts/TTF/DejaVuSans.ttf',11) if Path('/usr/share/fonts/TTF/DejaVuSans.ttf').exists() else ImageFont.load_default()
    canvas=Image.new('RGB',(columns*cw,32+((len(items)+columns-1)//columns)*ch),(26,26,28))
    d=ImageDraw.Draw(canvas);d.text((6,7),title,font=font,fill='white')
    for i,(filename,label) in enumerate(items):
        im=Image.open(filename).convert('RGBA')
        im.thumbnail((cw-8,ch-38),Image.Resampling.LANCZOS)
        x=(i%columns)*cw+(cw-im.width)//2;y=32+(i//columns)*ch
        canvas.paste(im,(x,y),im)
        d.text(((i%columns)*cw+4,y+ch-34),label,font=font,fill='white')
    canvas.save(path)


def main():
    records=json.loads((ROOT/'analysis/tim2_manifest.json').read_text())
    out=ROOT/'assets/tim2';out.mkdir(parents=True,exist_ok=True)
    previews=ROOT/'previews';previews.mkdir(exist_ok=True)
    cache={};exported=[];large=[];allitems=[]
    for r in records:
        entry=r['entry'];off=r['relative_offset']
        if entry not in cache:cache[entry]=(ROOT/f'assets/pac/{entry:04d}.dat').read_bytes()
        name=f'{entry:04d}_{off:08x}'
        blob=cache[entry][off:off+16+r['total_size']]
        if len(blob)!=16+r['total_size']:raise ValueError('Truncated TIM2')
        (out/f'{name}.tm2').write_bytes(blob)
        indices,rgba,display=decode(blob,r)
        if indices is not None:
            Image.fromarray(indices).save(out/f'{name}_indices.png')
        rec=dict(r,name=name,tm2_sha256=hashlib.sha256(blob).hexdigest())
        if rgba is not None:
            Image.fromarray(rgba).save(out/f'{name}_raw-alpha.png')
            Image.fromarray(display).save(out/f'{name}.png')
            rec.update(alpha_min=int(rgba[:,:,3].min()),alpha_max=int(rgba[:,:,3].max()))
            item=(out/f'{name}.png',f'{name}\n{r["width"]}x{r["height"]} / type{r["image_type"]}')
            allitems.append(item)
            if r['width']>=256 and r['height']>=192:large.append(item)
        else:
            rec['warning']='No embedded CLUT: index plane exported, NOT a decoded color image'
        exported.append(rec)
    (ROOT/'analysis/decoded_manifest.json').write_text(json.dumps(exported,indent=2)+'\n')
    for i in range(0,len(large),40):
        contact_sheet(large[i:i+40],previews/f'large_{i//40+1:02d}.jpg',5,(224,232),'Large TIM2 textures (GS-alpha display, black backdrop)')
    for i in range(0,len(allitems),100):
        contact_sheet(allitems[i:i+100],previews/f'all_{i//100+1:02d}.jpg',10,(160,168),'All decoded TIM2 textures')
    print(f'Exported {len(records)} original TM2s; {len(allitems)} color decodes; {len(large)} large images')


if __name__=='__main__':main()
