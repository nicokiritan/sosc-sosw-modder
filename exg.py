import os
import io
import glob
import pathlib
import shutil
import math
import json

import zstandard
from PIL import Image


EXG_SIGNATURE = b'EXGr'
BITMAP_SIGNATURE = b'BM'
ZSTANDARD_SIGNATURE = b'\x28\xB5\x2F\xFD'
DDS_SIGNATURE = b'\x44\x44\x53\x20'
EXGSET_SIGNATURE= b'YPAC'
EXGSET_FILE_NAME_LENGTH = 64

def iterate_pixels(data):
  pos = 0
  while pos < len(data):
    yield((data[pos+2], 
    data[pos+1], data[pos], data[pos+3]))
    pos += 4

def iterate_rgba_to_bgra(data):
  pos = 0
  while pos < len(data):
    yield data[pos+2]
    yield data[pos+1]
    yield data[pos]
    yield data[pos+3]
    pos += 4
  
def save_texture_as_png(dst_path, data, width):
  width = int(width)
  height = int(math.ceil(len(data)/4/width))
  img = Image.new("RGBA", (width, height))
  img.putdata(tuple(iterate_pixels(data)))
  img.save(dst_path)

def file_name_bytes_to_str(bytes):
  terminate_pos = bytes.find(b'\x00')
  if terminate_pos == -1:
    return bytes.decode("utf-8")
  return bytes[0:terminate_pos].decode("utf-8")

def str_to_file_name_bytes(name, length):
  b = name.encode("utf-8")
  b = b + bytes((0,)*(length - len(b)))
  return b

class EXGSet:
  def __init__(self, *, path=None):
    self.files = []
    self.misc_files = []
    self.head = b''

    if path is not None:
      self.init_with_path(path)

  def init_with_path(self, path):
    print("init_with_path")
    with open(path + ".hed", "rb") as hed_f, open(path + ".dat", "rb") as dat_f:
      if hed_f.read(4) != EXGSET_SIGNATURE:
        raise Exception("Sigunature is not YPAC.")
      self.head = hed_f.read(12)

      while True:
        file_name_bytes = hed_f.read(EXGSET_FILE_NAME_LENGTH)
        if len(file_name_bytes) < EXGSET_FILE_NAME_LENGTH:
          break
        file_name = file_name_bytes_to_str(file_name_bytes)
        file_size = int.from_bytes(hed_f.read(4), byteorder="little")
        file_position = int.from_bytes(hed_f.read(4), byteorder="little")
        
        dat_f.seek(file_position)
        print("load: " + file_name)
        if file_name[-4:] == ".exg":
          exg = EXGFile(name=file_name, stream=dat_f)
          self.files.append(exg)
        else:
          self.misc_files.append({
            "name": file_name,
            "data": dat_f.read(file_size)
          })

  def init_with_dir(self, path):
    path = pathlib.Path(path)

    with open(path / "info.json", "r") as f:
      info = json.load(f)
    self.head = bytes.fromhex(info["head"])
    
    files = os.listdir(path)
    exg_dir_names = [f for f in files if os.path.isdir(path / f) and f != "misc"]
    for dir_name in exg_dir_names:
      print("load: " + dir_name)
      exg = EXGFile(name=dir_name)
      exg.init_with_dir(path / dir_name)
      self.files.append(exg)

    files = os.listdir(path / "misc")
    for file_name in files:
      print("load: " + file_name)
      with open(path / "misc" / file_name, "rb") as f:
        self.misc_files.append({
          "name": file_name,
          "data": f.read()
        })


  def save(self, path):
    with open(path + ".dat", "wb") as dat_s, open(path + ".hed", "wb") as  hed_s:
      hed_s.write(EXGSET_SIGNATURE)
      hed_s.write(self.head)

      current_pos = 0
      for exg in self.files:
        print("write:" +  exg.name)
        data = exg.serialize()
        dat_s.write(data)
        hed_s.write(str_to_file_name_bytes(exg.name, EXGSET_FILE_NAME_LENGTH))
        hed_s.write(len(data).to_bytes(4, "little"))
        hed_s.write(current_pos.to_bytes(4, "little"))
        current_pos += len(data)

      for misc_file in self.misc_files:
        print("write:" +  misc_file["name"])
        data = misc_file["data"]
        dat_s.write(data)
        hed_s.write(str_to_file_name_bytes(misc_file["name"], EXGSET_FILE_NAME_LENGTH))
        hed_s.write(len(data).to_bytes(4, "little"))
        hed_s.write(current_pos.to_bytes(4, "little"))
        current_pos += len(data)

  def unpack(self, path):
    path = pathlib.Path(path)
    os.makedirs(path, exist_ok=True)
    
    # unpack info
    info = {}
    info["head"] = self.head.hex()
    with open(path / "info.json", "w") as f:
      json.dump(info, f)

    os.makedirs(path / "misc", exist_ok=True)
    for misc_file in self.misc_files:
      print("unpack " + misc_file["name"])
      with open(path / "misc" / misc_file["name"], "wb") as f:
        f.write(misc_file["data"])

    # unpack exg files
    for i in range(len(self.files)):
      exg_file = self.files[i]
      print("unpack " + exg_file.name)
      exg_file.unpack(path / exg_file.name)

class EXGFile:
  def __init__(self, *, name="", stream=None):
    self.items = []
    self.name = name

    if stream is not None:
      self.init_with_stream(stream)
  
  def init_with_stream(self, stream):
    magic = stream.read(4)
    if magic != EXG_SIGNATURE:
      raise Exception("Magic nWumber is not EXGr")

    items_count = int.from_bytes(stream.read(4), byteorder="little")
    for i in range(items_count):
      item = EXGItem(stream=stream)
      self.items.append(item)
  
  def init_with_dir(self, path):
    path = pathlib.Path(path)
    files = os.listdir(path)
    dir_names = [f for f in files if os.path.isdir(path / f)]
    for dir_name in dir_names:
      item = EXGItem()
      item.init_with_dir(path / dir_name)
      self.items.append(item)

  def serialize(self):
    stream = io.BytesIO()
    stream.write(EXG_SIGNATURE)
    stream.write(len(self.items).to_bytes(4, "little"))
    for item in self.items:
      stream.write(item.serialize())
    result = stream.getvalue()
    stream.close()
    return result

  def unpack(self, dst_path):
    path = pathlib.Path(dst_path)
    os.makedirs(path, exist_ok=True)
    for i in range(len(self.items)):
      self.items[i].unpack(path / str(i))

class EXGItem:
  def __init__(self, *, stream=None):
    self.width = 0
    self.head = b''
    self.data = b''

    if stream is not None:
      self.init_with_stream(stream)
  
  def init_with_stream(self, stream):
    data_size = int.from_bytes(stream.read(4), byteorder="little")
    self.width = int(int.from_bytes(stream.read(4), byteorder="little")/4)
    self.head = stream.read(24)
    self.data = stream.read(data_size)
  
  def init_with_dir(self, path):
    path = pathlib.Path(path)
    with open(path / "info.json", "r") as f:
      info = json.load(f)
    self.width = info["width"]
    self.head = bytes.fromhex(info["head"])

    ## RAW
    if os.path.exists(path / "data.bin"):
      with open(path / "data.bin", "rb") as f:
        self.data = f.read()
    else:
      compressor = zstandard.ZstdCompressor()
      # load png
      if os.path.exists(path / "data.png"):
        image = Image.open(path / "data.png").convert('RGBA')
        self.width = image.width
        data = bytes(tuple(iterate_rgba_to_bgra(image.tobytes())))
        comp_data = compressor.compress(data)
        self.data = comp_data
      ## DDS
      elif os.path.exists(path / "data.dds"):
        with open(path / "data.dds") as f:
          data = f.read()
        comp_data = compressor.compress(data)
        self.data = comp_data
      else:
        self.data = b''
        
  def serialize(self):
    stream = io.BytesIO()
    stream.write(len(self.data).to_bytes(4, "little"))
    stream.write(int(self.width*4).to_bytes(4, "little"))
    stream.write(self.head)
    stream.write(self.data)
    result = stream.getvalue()
    stream.close()
    return result

  def unpack(self, dst_path, debug=False):
    path = pathlib.Path(dst_path)
    os.makedirs(path, exist_ok=True)

    # Save info
    info = {}
    info["width"] = self.width
    info["head"] = self.head.hex()
    with open(path / "info.json", "w") as f:
      json.dump(info, f)
    
    # Save data as raw
    if self.data[0:4] != ZSTANDARD_SIGNATURE:
      with open(path / "data.bin", "wb") as f:
        f.write(self.data)

    # Save data as image
    else:
      decompressor = zstandard.ZstdDecompressor()
      decomp_data = decompressor.decompress(self.data)
      if debug:
        with open(path / "data.bin", "wb") as f:
          f.write(decomp_data)
      # DDS
      if decomp_data[0:4] == DDS_SIGNATURE:
        with open(path / "data.dds", "wb") as f:
          f.write(decomp_data)
      # Bitmap
      elif decomp_data[0:2] == BITMAP_SIGNATURE:
        with open(path / "data.bmp", "wb") as f:
          f.write(decomp_data)
      else:
        save_texture_as_png(path / "data.png", decomp_data, self.width)

