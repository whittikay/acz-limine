#!/usr/bin/env python3
"""Reconstruct a reference-matched clean MainSelect background using game textures.
An approximate static additive composite; NOT a decoded SWG/GS animation frame.
No screenshot pixels are sampled into any artwork or wallpaper.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from analyze_reference import sample_shift,robust_fit
from decode_tim2 import contact_sheet
from make_wallpapers import contrast_white,save_png
from pac_extract import ROOT


def combine(base,camera,lights,gains):
    return np.clip(base*gains[0]+camera*gains[1]+lights*gains[2],0,255).round().astype('uint8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder=ROOT/'analysis/reference'
    fit=json.loads((folder/'fit.json').read_text())
    original=ROOT/fit['reference'];reference_hash=digest(original)
    sources=[ROOT/f'assets/tim2/{name}.png' for name in fit['sources']]
    sources_hash={str(p.relative_to(ROOT)):digest(p) for p in sources}
    ims=[Image.open(p).convert('RGB') for p in sources]
    common=dict(dx=fit['fit_source_sample_shift'][0],dy=fit['fit_source_sample_shift'][1],sx=fit['fit_source_x_scale'])
    base,camera=[sample_shift(im.filter(ImageFilter.GaussianBlur(fit['fit_filter_radius'])),**common) for im in ims[:2]]
    light_im=ims[2].filter(ImageFilter.GaussianBlur(fit['light_fit_filter_radius']))
    lights=sample_shift(light_im,*fit['light_fit_sample_shift'],fit['light_fit_source_x_scale'])
    gains=[fit['base_gain'],fit['camera_gain'],fit['light_gain']]
    if any(not np.isfinite(g) or not 0<=g<=2 for g in gains):raise ValueError('Invalid fitted layer gain')
    result=Image.fromarray(combine(base,camera,lights,gains))
    out=ROOT/'artwork/reconstructed';out.mkdir(exist_ok=True)
    native=out/'acz-main-menu-layered-reference-fit-512x448.png'
    save_png(result,native,'Reference-estimated additive composition of three original MainSelect textures. Not an original single texture, exact SWG frame, or screenshot with UI removed.')
    # Export per-step diagnostics; all have ONLY source texture pixels.
    stage_paths=[]
    for label,array in [('red-grid',base*gains[0]),('red-plus-blue',base*gains[0]+camera*gains[1]),('particles-only',lights*gains[2])]:
        path=folder/f'{label}.png'
        Image.fromarray(np.clip(array,0,255).round().astype('uint8')).save(path)
        stage_paths.append(path)
    preview=ROOT/'previews/acz-main-menu-layered-960x540.png'
    cropped=result.resize((3840,2880),Image.Resampling.LANCZOS).crop((0,360,3840,2520))
    cropped.resize((960,540),Image.Resampling.LANCZOS).save(preview)
    walls=[]
    # The reference's tiny highlights put 179 pixels below 4.5:1 white contrast.
    # Offer a separately labeled 10%-darker derivative, not a changed reference fit.
    limine=Image.fromarray((np.asarray(cropped,dtype=float)*0.9).round().astype('uint8'))
    for label,im,framing in [('',cropped,'4:3 interpretation, resize 3840x2880, crop y=360..2519'),
                            ('-full-field',result.resize((3840,2160),Image.Resampling.LANCZOS),'Entire native texture field stretched anamorphically to 16:9; no crop'),
                            ('-limine',limine,'Same framing as cropped version; RGB multiplied by 0.90 for minimum white-text contrast above 4.5:1')]:
        dest=ROOT/f'wallpapers/acz-main-menu-layered-3840x2160{label}.png'
        save_png(im,dest,'Clean MainSelect background reconstructed from original red-grid, blue-image, and particle textures; screenshot-estimated additive blend, not a decoded game frame. '+framing)
        with Image.open(dest) as check:
            check.load()
            if check.size!=(3840,2160) or check.mode!='RGB':raise ValueError('Invalid wallpaper')
        walls.append(dict(path=str(dest.relative_to(ROOT)),size=[3840,2160],mode='RGB',framing=framing,
                          minimum_white_text_contrast=contrast_white(im),sha256=digest(dest)))
    # Comparison includes the screenshot in a labeled preview only, NEVER in result.
    contact_sheet([(stage_paths[0],'Extracted red grid (registered)'),
                   (stage_paths[1],'+ faint blue image (estimated additive blend)'),
                   (native,'+ original highlight spots = clean static composite'),
                   (folder/'reference-512x448.png','PCSX2 reference with UI (comparison ONLY)')],
                  ROOT/'previews/main-menu-layered-comparison.jpg',2,(640,544),
                  'Original texture layers vs reference: fitted static composition, not an exact game frame')
    annotated=Image.open(folder/'reference-512x448.png').convert('RGB').resize((1024,896),Image.Resampling.BICUBIC)
    d=ImageDraw.Draw(annotated)
    sx=fit['light_fit_source_x_scale'];dx,dy=fit['light_fit_sample_shift']
    for i,r in enumerate(fit['spot_measurements']):
        x,y=r['source_xy'];px=(x-(1-sx)*256-dx)/sx*2;py=(y-dy)*2
        d.ellipse((px-16,py-16,px+16,py+16),outline=(0,255,210),width=2)
        d.text((px+18,py-12),str(i+1),fill=(0,255,210))
    annotated.save(ROOT/'previews/reference-matched-spots.png')
    target=np.asarray(Image.open(folder/'reference-512x448.png'),float)
    mask=np.asarray(Image.open(folder/'ui-free-fit-mask.png'))>0
    _,base_error=robust_fit(base[mask].reshape(-1,1),target[mask].reshape(-1))
    metrics=dict(base_only_best_gain_mae=float(np.mean(abs(base_error))),
                 base_plus_blue_mae=fit['background_fit_mae'],
                 base_plus_blue_median_error=fit['background_fit_median_abs_error'],
                 particle_patch_mae=fit['particle_fit_mae'],
                 units='8-bit RGB levels, registered native-resolution comparison')
    manifest=dict(kind='Approximate static reconstruction from original extracted layers',
                  native_artwork=str(native.relative_to(ROOT)),native_sha256=digest(native),
                  reference=fit['reference'],reference_sha256=reference_hash,
                  sources_sha256=sources_hash,fit_parameters='analysis/reference/fit.json',
                  gains=gains,metrics=metrics,wallpapers=walls,
                  screenshot_pixels_in_artwork=False,
                  caveat='Effective RGB blend gains/registration estimated from one screenshot; not decoded GS alpha, exact blend equation, or animation timing. Base/blue and particles are registered separately. Both effect textures have constant raw GS alpha 128; there is no embedded per-pixel opacity mask in them.')
    (folder/'layered_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if digest(original)!=reference_hash:raise ValueError('Reference screenshot changed')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
