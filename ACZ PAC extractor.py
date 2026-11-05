import os
import textwrap
import os.path
import shutil

def tbl():
    try:
        tbl_file = open("data.tbl", "rb")
    except FileNotFoundError as x:
        print ()
        print ("///ERROR///: DATA.TBL file not found.")
        print ()
        a = input("///INPUT///: Press any key to exit...")
        if a:
            exit(0)
        else:
            exit(0)
    else:
        return tbl_file

def pac():
    try:
        pac_file = open("data.pac", "rb")
    except FileNotFoundError as x:
        print ()
        print ("///ERROR///: DATA.PAC file not found.")
        print ()
        a = input("///INPUT///: Press any key to exit...")
        if a:
            exit(0)
        else:
            exit(0)
    else:
        return pac_file

def extraction(tbl_file, pac_file):
    val = 0
    f_n = 0
    f_offset = 8
    offset_list = []
    size_list = []
    tbl_file.seek(0, 0)
    tbl_nof = int.from_bytes(tbl_file.read(4), byteorder = "little")
    for f in range(tbl_nof):
        tbl_file.seek(f_offset, 0)
        offset_list.append(int.from_bytes(tbl_file.read(4), byteorder = "little"))
        f_offset = f_offset + 4
        tbl_file.seek(f_offset, 0)
        size_list.append(int.from_bytes(tbl_file.read(4), byteorder = "little"))
        f_offset = f_offset + 4
    for f in range(tbl_nof):
        fname = "DATA//" + str(f_n).zfill(4) + ".dat"
        file = open(fname, "wb")
        pac_file.seek(offset_list[val])
        data = pac_file.read(size_list[val])
        file.write(data)
        file.close()
        print ("file:", fname, "offset:", hex(offset_list[val]), "size:", size_list[val])
        val = val + 1
        f_n = f_n + 1

print(textwrap.fill("Ace Combat 5/ZERO DATA.PAC content extractor by death_the_d0g", width = 80))
print(textwrap.fill("=============================================================", width = 80))
print()
print(textwrap.fill("Extracts the contents of the DATA.PAC file.", width = 80))
print()

if os.path.exists("DATA"):
    shutil.rmtree("DATA")
    os.mkdir("DATA")
else:
    os.mkdir("DATA")

tbl_file = tbl()
pac_file = pac()
extraction(tbl_file, pac_file)
tbl_file.close()
pac_file.close()
os.remove("data.pac")
os.remove("data.tbl")

