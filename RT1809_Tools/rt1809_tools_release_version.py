import re
import pathlib

# 读取 main.py 获取 __version__ = "..."
main_file = pathlib.Path("rt1809_tools_config.py").read_text(encoding="utf-8")
match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', main_file)
if not match:
    raise RuntimeError("在 rt1809_tools_config.py 中未找到 __version__ 定义！")

version = match.group(1)  # e.g. "1.0.0"

# 解析成 1,0,0,0 四段式
parts = version.split(".")
parts = (parts + ["0", "0", "0", "0"])[:4]  # 补足长度
filevers = ",".join(parts)
prodvers = filevers

# 生成 version.txt 内容
template = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({filevers}),
    prodvers=({prodvers}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName',  u'Racer-Tech'),
        StringStruct(u'FileDescription', u'UpgradeTool for Racer-Tech'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'UpgradeTool'),
        StringStruct(u'OriginalFilename', u'UpgradeTool.exe'),
        StringStruct(u'ProductName', u'Racer-Tech UpgradeTool'),
        StringStruct(u'ProductVersion', u'{version}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""

pathlib.Path("rt1809_tools_version.txt").write_text(template.strip(), encoding="utf-8-sig")  
# 用 utf-8 带 BOM，PyInstaller 要求
print(f"已生成 rt1809_tools_version.txt (版本号: {version})")