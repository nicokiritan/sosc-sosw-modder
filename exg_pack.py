import sys

import exg

if len(sys.argv) < 2:
  print("drag&drop .exg.unpack directory")
  input()
  exit()

target_dirs = sys.argv[1:]

for target_dir in target_dirs:
  print("Start packing " + target_dir)
  if target_dir[-11:] != ".exg.unpack":
    print("extension is not .exg.unpack")
    continue

  try:
    exg_file = exg.EXGFile()
    exg_file.init_with_dir(target_dir)
    data = exg_file.serialize()
    with open(target_dir[0:-7], "wb") as f:
      f.write(data)
    print("Packing successful")

  except Exception as e:
    print("packing unsuccessful")
    print(e)

print("end")
input()