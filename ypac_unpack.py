
import os
import sys
import exg

if len(sys.argv) < 3:
  print("Drag&drop .dat and .hed")
  input()
  exit()

dat_path = ""
hed_path = ""

drop_files = sys.argv[1:]
for drop_file in drop_files:
  if drop_file[-4:] == ".dat":
    dat_path = drop_file
  elif drop_file[-4:] == ".hed":
    hed_path = drop_file

if dat_path == "" or hed_path == "":
  print("Drag&drop .dat and .hed")
  input()
  exit()

if dat_path[0:-4] != hed_path[0:-4]:
  print(".dat and .hed file names are must be the same.")
  input()
  exit()

target_file = dat_path[0:-4]

try:
  exgset = exg.EXGSet(path=target_file)
  print("Start unpacking portrait...")
  exgset.unpack(target_file + ".unpack")
  print("Unpacking successful")

except Exception as err:
  print("Unpacking failed")
  print(err)

print("end")
input()