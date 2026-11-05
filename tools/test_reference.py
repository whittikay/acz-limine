#!/usr/bin/env python3
import unittest
import numpy as np
from PIL import Image
from analyze_reference import robust_fit,sample_shift
from reconstruct_main_menu import combine


class ReferenceTests(unittest.TestCase):
    def test_known_blend_fit(self):
        rng=np.random.default_rng(0)
        design=rng.uniform(0,255,(1000,2))
        target=design@np.array([0.99,0.074])
        target[::40]+=50  # Sparse UI-like outliers must not dominate the fit.
        gain,error=robust_fit(design,target,iterations=20,delta=0.1)
        np.testing.assert_allclose(gain,[0.99,0.074],atol=0.001)

    def test_black_is_neutral_for_additive_layers(self):
        base=np.full((4,4,3),50.0);black=np.zeros_like(base)
        np.testing.assert_array_equal(combine(base,black,black,[1,0.074,0.74]),base.astype('uint8'))
        camera=np.full_like(base,100)
        np.testing.assert_array_equal(combine(base,camera,black,[1,0.1,0.74]),np.full((4,4,3),60,dtype='uint8'))

    def test_sampler_identity_and_output_bounds(self):
        rng=np.random.default_rng(1)
        source=rng.integers(0,255,(5,7,3),dtype='uint8')
        np.testing.assert_array_equal(sample_shift(Image.fromarray(source),0,0,1),source)
        result=combine(np.full((1,1,3),250.0),np.full((1,1,3),100.0),np.zeros((1,1,3)),[1,1,1])
        np.testing.assert_array_equal(result,[[[255,255,255]]])


if __name__=='__main__':unittest.main()
