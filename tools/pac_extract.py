#!/usr/bin/env python3
"""Read-only Ace Combat 5/Zero PAC reader (based on death_the_d0g's table layout).

Unlike the original community script, this NEVER deletes inputs or output trees.
Paths default to the project directory, not the shell's current directory.
Only explicit --indices/--all extracts data; default is validation + inventory.
"""
from pathlib import Path
import argparse
import bisect
import csv
import hashlib
import json
import mmap
import struct

ROOT = Path(__file__).resolve().parent.parent


def resolve_input(directory, name):
    matches = [p for p in Path(directory).iterdir() if p.name.casefold() == name.casefold() and p.is_file()]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one case-insensitive {name} in {directory}, found {len(matches)}")
    return matches[0]


def read_table(table, pac_size):
    raw = Path(table).read_bytes()
    if len(raw) < 8:
        raise ValueError('Truncated TBL header')
    count, reserved = struct.unpack_from('<II', raw)
    if not count or len(raw) != 8 + count * 8:
        raise ValueError('Invalid TBL count/length')
    if reserved != 0:
        raise ValueError(f'Unrecognized reserved header: {reserved:#x}')
    rows = list(struct.iter_unpack('<II', raw[8:]))
    end = 0
    for i, (offset, size) in enumerate(rows):
        if not size or offset < end or offset + size > pac_size:
            raise ValueError(f'Invalid/overlapping entry {i}: {offset:#x}+{size:#x}')
        end = offset + size
    return rows


def sub_offsets(data, start, size):
    """Conservatively recognize a count + ascending relative-offset directory."""
    if size < 8:
        return None
    count = struct.unpack_from('<I', data, start)[0]
    if not 0 < count <= 10000 or 4 + 4 * count > size:
        return None
    offsets = struct.unpack_from(f'<{count}I', data, start + 4)
    if offsets[0] < 4 + 4 * count or offsets[-1] >= size:
        return None
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        return None
    return offsets


def tim2_header(data, pos, end):
    if pos + 64 > end or data[pos:pos+4] != b'TIM2':
        return None
    version, alignment, pictures = struct.unpack_from('<BBH', data, pos + 4)
    if version not in (3, 4) or alignment not in (0, 1) or not 0 < pictures < 256:
        return None
    pic = pos + (16 if alignment == 0 else 128)
    if pic + 48 > end:
        return None
    total, clut, image, header, colors, fmt, mipmaps, clut_type, image_type, width, height = struct.unpack_from('<IIIHHBBBBHH', data, pic)
    if header < 48 or total < header + clut + image or pic + total > end:
        return None
    if not (0 < width <= 4096 and 0 < height <= 4096) or image_type not in (1,2,3,4,5):
        return None
    return dict(offset=pos, version=version, alignment=alignment, pictures=pictures,
                picture_offset=pic, total_size=total, header_size=header,
                clut_size=clut, image_size=image, clut_colors=colors,
                image_type=image_type, clut_type=clut_type, format=fmt,
                mipmaps=mipmaps, width=width, height=height)


def inventory(pac, rows):
    starts = [o for o,s in rows]
    textures = []
    counts = [0] * len(rows)
    with pac.open('rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as data:
        pos = 0
        while (pos := data.find(b'TIM2', pos)) != -1:
            i = bisect.bisect_right(starts, pos) - 1
            header = tim2_header(data, pos, starts[i] + rows[i][1])
            if header:
                header.update(entry=i, relative_offset=pos-starts[i])
                textures.append(header)
                counts[i] += 1
            pos += 4
        result = []
        for i,(offset,size) in enumerate(rows):
            subs = sub_offsets(data, offset, size)
            kind = 'offset-table container' if subs is not None else 'unclassified binary'
            if counts[i]:
                kind += ' / embedded TIM2'
            result.append(dict(index=i, filename=f'{i:04d}.dat', pac_offset=offset,
                               size=size, detected_type=kind, subentries=len(subs) if subs else 0,
                               tim2_count=counts[i], signature_hex=data[offset:offset+32].hex()))
    return result, textures


def parse_indices(text, count):
    indices = set()
    for part in text.split(','):
        limits = part.split('-')
        if len(limits) == 1:
            indices.add(int(part))
        elif len(limits) == 2:
            lo, hi = map(int, limits)
            if lo > hi:
                raise ValueError('Reversed range')
            indices.update(range(lo, hi + 1))
        else:
            raise ValueError('Invalid indices')
    if any(not 0 <= i < count for i in indices):
        raise ValueError('Entry index out of range')
    return sorted(indices)


def extract(pac, rows, indices, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    destinations = [output / f'{i:04d}.dat' for i in indices]
    if any(p.exists() for p in destinations):
        raise FileExistsError('Refusing to overwrite an existing extracted file')
    results = []
    with pac.open('rb') as source:
        for i,dest in zip(indices,destinations):
            offset,size = rows[i]
            source.seek(offset)
            digest = hashlib.sha256()
            remaining = size
            with dest.open('xb') as target:
                while remaining:
                    block = source.read(min(remaining, 1 << 20))
                    if not block:
                        raise EOFError(f'Short PAC read for entry {i}')
                    target.write(block)
                    digest.update(block)
                    remaining -= len(block)
            # Independently verify the written file, not merely the source read.
            if hashlib.sha256(dest.read_bytes()).hexdigest() != digest.hexdigest():
                raise IOError(f'Output verification failed: {dest}')
            results.append(dict(index=i, path=str(dest), offset=offset, size=size, sha256=digest.hexdigest()))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT)
    p.add_argument('--inventory', type=Path)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--indices', help='e.g. 1236-1256,1426-1429')
    group.add_argument('--all', action='store_true', help='Extract all entries (not needed for texture investigation)')
    p.add_argument('--output', type=Path, default=ROOT/'assets'/'pac')
    args = p.parse_args()
    pac = resolve_input(args.source, 'DATA.PAC')
    table = resolve_input(args.source, 'DATA.TBL')
    rows = read_table(table, pac.stat().st_size)
    print(f'Validated {len(rows)} entries; {sum(s for o,s in rows):,} payload bytes; PAC {pac.stat().st_size:,} bytes')
    if args.inventory:
        records,textures = inventory(pac,rows)
        args.inventory.mkdir(parents=True,exist_ok=True)
        with (args.inventory/'inventory.csv').open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
        with (args.inventory/'tim2_manifest.json').open('x') as f:
            json.dump(textures,f,indent=2)
        print(f'Found {len(textures)} structurally valid TIM2 resources in {sum(bool(r["tim2_count"]) for r in records)} PAC entries')
    if args.all or args.indices:
        if (args.output/'extraction_manifest.json').exists():
            raise FileExistsError('Choose a fresh output directory: extraction manifest already exists')
        indices = list(range(len(rows))) if args.all else parse_indices(args.indices,len(rows))
        extracted = extract(pac,rows,indices,args.output)
        with (args.output/'extraction_manifest.json').open('x') as f:
            json.dump(extracted,f,indent=2)
        print(f'Extracted and SHA-256 verified {len(extracted)} files, {sum(r["size"] for r in extracted):,} bytes')


if __name__ == '__main__':
    main()
