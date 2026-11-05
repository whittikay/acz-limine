#!/usr/bin/env python3
import unittest
import numpy as np
from decode_tim2 import decode
from pac_extract import tim2_header


class Tim2Tests(unittest.TestCase):
    def record(self,w,h,typ,colors):
        return dict(width=w,height=h,image_type=typ,clut_colors=colors,
                    clut_type=3,pictures=1,mipmaps=1,alignment=0,header_size=48,
                    image_size=(w*h//2 if typ==4 else w*h),clut_size=colors*4)

    def test_low_nibble_first_and_raw_alpha(self):
        r=self.record(2,1,4,16)
        pal=np.zeros((16,4),dtype=np.uint8)
        pal[1]=[12,34,56,64];pal[2]=[98,76,54,128]
        indices,rgba,display=decode(bytes(64)+b'\x21'+pal.tobytes(),r)
        self.assertEqual(indices.tolist(),[[1,2]])
        self.assertEqual(rgba[0].tolist(),[[12,34,56,64],[98,76,54,128]])
        self.assertEqual(display[0,:,3].tolist(),[128,255])

    def test_csm1_permutation(self):
        r=self.record(4,1,5,256)
        pal=np.zeros((256,4),dtype=np.uint8)
        pal[:,0]=np.arange(256);pal[:,3]=128
        indices,rgba,display=decode(bytes(64)+bytes([0,8,16,24])+pal.tobytes(),r)
        self.assertEqual(rgba[0,:,0].tolist(),[0,16,8,24])
        r['clut_type']=0x83
        indices,rgba,display=decode(bytes(64)+bytes([0,8,16,24])+pal.tobytes(),r)
        self.assertEqual(rgba[0,:,0].tolist(),[0,8,16,24])

    def test_bounds_and_unsupported(self):
        self.assertIsNone(tim2_header(b'TIM2'+bytes(60),0,64))
        r=self.record(4,1,4,16)
        with self.assertRaises(ValueError):decode(bytes(64)+b'\x12',r)
        r=self.record(2,1,1,0)
        with self.assertRaises(ValueError):decode(bytes(64),r)


if __name__=='__main__':unittest.main()
