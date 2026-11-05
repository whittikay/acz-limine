#!/usr/bin/env python3
"""Register extracted MainSelect layers to a supplied PCSX2 screenshot.
This estimates a static additive composite, not a decoded SWG/GS draw state.
Screenshot pixels are ONLY used for comparison/fitting, never pasted into artwork.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter
from pac_extract import ROOT


def robust_fit(a,b,iterations=10,delta=2.0):
    weights=np.ones(len(b))
    for _ in range(iterations):
        co=np.linalg.lstsq(a*weights[:,None],b*weights,rcond=None)[0]
        residual=b-a@co
        # weights multiply both design and response, hence sqrt for Huber IRLS
        weights=np.sqrt(np.minimum(1,delta/np.maximum(1e-9,abs(residual))))
    return co,residual


def sample_shift(im,dx,dy,sx=1.0):
    # Centered affine sampling; sx<1 stretches the source across the output.
    return np.asarray(im.transform(im.size,Image.Transform.AFFINE,(sx,0,(1-sx)*256+dx,0,1,dy),Image.Resampling.BILINEAR),dtype=np.float64)


def main():
    out=ROOT/'analysis/reference';out.mkdir(exist_ok=True)
    paths=sorted((ROOT/'example from pcsx2').glob('*.png'))
    if len(paths)!=1:raise ValueError('Expected exactly one reference PNG')
    original=Image.open(paths[0]).convert('RGB')
    # Four black rows precede the game image in this capture; no image content cropped.
    crop=(0,4,original.width,original.height)
    reference=original.crop(crop).resize((512,448),Image.Resampling.BILINEAR)
    reference.save(out/'reference-512x448.png')
    target=np.asarray(reference,dtype=np.float64)
    names=['1239_00163d60','1239_000f2940','1239_0012ada0']
    images=[Image.open(ROOT/f'assets/tim2/{n}.png').convert('RGB') for n in names]
    y,x=np.mgrid[:448,:512]
    # Explicit, conservative UI-free sampling areas for background/camera fit.
    mask=(y>=379)|((y<=23))|((x<17)|(x>493))|((x>30)&(x<205)&(y>180)&(y<327))
    # Reject particle pixels for this first fit; characterize lights separately below.
    light=np.asarray(images[2],dtype=float)
    mask &= np.max(light,axis=2)<2
    model_results=[]
    # At native size the reference has filtering from both the renderer and resize.
    # Search only subpixel alignment and small lowpass radii, not arbitrary warps.
    for radius in (0.35,0.65):
        ims=[im.filter(ImageFilter.GaussianBlur(radius)) for im in images[:2]]
        for sx in (0.98,0.984375,0.99,0.995,1.0):
            for dy in (-1,-0.5,0,0.5):
                for dx in (-0.5,0,0.5,1):
                    arrays=[sample_shift(im,dx,dy,sx) for im in ims]
                    a=np.stack([arrays[0][mask],arrays[1][mask]],axis=-1).reshape(-1,2)
                    b=target[mask].reshape(-1)
                    co,residual=robust_fit(a,b,delta=2)
                    loss=float(np.mean(np.minimum(residual**2,16)))
                    # Store parameters only, not hundreds of full image arrays.
                    model_results.append((loss,radius,sx,dx,dy,co))
    loss,radius,sx,dx,dy,co=min(model_results,key=lambda r:r[0])
    base,camera=[sample_shift(im.filter(ImageFilter.GaussianBlur(radius)),dx,dy,sx) for im in images[:2]]
    residual=(target-base*co[0]-camera*co[1])[mask].reshape(-1)
    fitted=base*co[0]+camera*co[1]
    # Known visible spots, with patches chosen to avoid menu text. The small spot
    # around (316,171) crosses CONTROLLER SETTINGS and is deliberately excluded.
    spots=[(82,323),(264,123),(328,157),(389,169),(475,216)]
    spotmask=np.zeros((448,512),dtype=bool)
    for xx,yy in spots:
        spotmask[yy-6:yy+7,xx-6:xx+7]=True
    light_results=[]
    for lradius in (0.0,0.35,0.5,0.65):
        lim=images[2].filter(ImageFilter.GaussianBlur(lradius)) if lradius else images[2]
        for lsx in (0.98,0.984375,0.99,1.0):
            for ldx in (-1,-0.5,0,0.5,1):
                for ldy in (-0.5,0,0.5,1):
                    light=sample_shift(lim,ldx,ldy,lsx)
                    a=light[spotmask].reshape(-1,1);b=(target-fitted)[spotmask].reshape(-1)
                    lgain,lerr=robust_fit(a,b,delta=5)
                    lloss=float(np.mean(np.minimum(lerr**2,225)))
                    light_results.append((lloss,lradius,lsx,ldx,ldy,float(lgain[0])))
    lloss,lradius,lsx,ldx,ldy,lgain=min(light_results,key=lambda r:r[0])
    light=sample_shift(images[2].filter(ImageFilter.GaussianBlur(lradius)) if lradius else images[2],ldx,ldy,lsx)
    lerr=(target-fitted-light*lgain)[spotmask].reshape(-1)
    measurements=[]
    for xx,yy in spots:
        region=(slice(yy-6,yy+7),slice(xx-6,xx+7))
        roi=np.max(light[region],axis=2)>8
        a=light[region][roi].reshape(-1,1);b=(target-fitted)[region][roi].reshape(-1)
        gain,error=robust_fit(a,b,delta=5)
        measurements.append(dict(source_xy=[xx,yy],gain=float(gain[0]),mae=float(np.mean(abs(error)))))
    combined=fitted+light*lgain
    Image.fromarray(np.clip(combined,0,255).round().astype('uint8')).save(out/'fitted-composite-512x448.png')
    # Make the blue residual and explicit fit masks inspectable.
    Image.fromarray(np.clip((target-base)*4+32,0,255).astype('uint8')).save(out/'reference-minus-base-amplified.png')
    Image.fromarray(mask.astype('uint8')*255).save(out/'ui-free-fit-mask.png')
    Image.fromarray(spotmask.astype('uint8')*255).save(out/'spot-fit-mask.png')
    result=dict(reference=str(paths[0].relative_to(ROOT)),reference_dimensions=list(original.size),
                reference_crop=list(crop),native_comparison_size=[512,448],sources=names,
                model='base_gain * red_grid + camera_gain * blue_image + light_gain * particle_image (RGB additive)',
                base_gain=float(co[0]),camera_gain=float(co[1]),light_gain=lgain,
                fit_filter_radius=radius,fit_source_x_scale=sx,fit_source_sample_shift=[dx,dy],
                light_fit_filter_radius=lradius,light_fit_source_x_scale=lsx,light_fit_sample_shift=[ldx,ldy],
                ui_free_pixels=int(mask.sum()),background_fit_mae=float(np.mean(abs(residual))),
                background_fit_median_abs_error=float(np.median(abs(residual))),
                particle_fit_mae=float(np.mean(abs(lerr))),spot_measurements=measurements,
                caveat='Blend weights and subpixel sampling are screenshot estimates, not decoded runtime parameters. No screenshot pixels are used in recovered artwork.')
    (out/'fit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
