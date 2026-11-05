#!/usr/bin/env python3
import struct
import tempfile
import unittest
from pathlib import Path
from pac_extract import read_table, resolve_input, extract, parse_indices


class PacTests(unittest.TestCase):
    def test_safety_and_case(self):
        # Tests create temporary files inside the project, never touch real archives.
        root = Path(__file__).resolve().parent.parent / 'analysis'
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as d:
            d=Path(d)
            pac=d/'DATA.PAC';pac.write_bytes(b'abcdefgh')
            tbl=d/'DATA.TBL';tbl.write_bytes(struct.pack('<6I',2,0,0,3,3,5))
            self.assertEqual(resolve_input(d,'data.tbl'),tbl)
            rows=read_table(tbl,8)
            result=extract(pac,rows,[1],d/'out')
            self.assertEqual((d/'out'/'0001.dat').read_bytes(),b'defgh')
            self.assertEqual(result[0]['size'],5)
            with self.assertRaises(FileExistsError): extract(pac,rows,[1],d/'out')
            self.assertEqual(pac.read_bytes(),b'abcdefgh')
            with self.assertRaises(ValueError): read_table(tbl,7)
            tbl.write_bytes(struct.pack('<6I',2,0,0,4,3,5))
            with self.assertRaises(ValueError): read_table(tbl,8)
            tbl.write_bytes(b'\x00')
            with self.assertRaises(ValueError): read_table(tbl,8)

    def test_selection(self):
        self.assertEqual(parse_indices('1,3-5,3',10),[1,3,4,5])
        with self.assertRaises(ValueError): parse_indices('10',10)
        with self.assertRaises(ValueError): parse_indices('5-1',10)


if __name__=='__main__': unittest.main()
