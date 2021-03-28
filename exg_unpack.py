import sys

import exg

if len(sys.argv) < 2:
  print("drag&drop .exg file")
  input()
  exit()

target_files = sys.argv[1:]

for target_file in target_files:
  print("Start unpacking " + target_file)
  if target_file[-4:] != ".exg":
    print("extension is not .exg")

  try:
    with open(target_file, "rb") as f:
      exg_file = exg.EXGFile(stream=f)
    exg_file.unpack(target_file + ".unpack")
    print("Unpacking successful")

  except Exception as e:
    print("Unpacking failed")
    print(e)
    
print("end")
input()

