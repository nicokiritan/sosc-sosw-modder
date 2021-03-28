import os
import sys
import exg

if len(sys.argv) < 2:
  print("Drag&drop .unpack directory")
  input()
  exit()

target_dir = sys.argv[1]

if target_dir[-7:] != ".unpack":
  print("Extension is not .unpack")
  input()
  exit()

print("Start packing " + target_dir)

try:
  exgset = exg.EXGSet()
  exgset.init_with_dir(target_dir)
  exgset.save(target_dir[0:-7])

  print("Packing successful")

except Exception as e:
  print("Packing failed")
  print(e)

print("end")
input()