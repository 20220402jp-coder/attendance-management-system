"""将当前系统的打包产物压缩为可发布文件。"""

import stat
import zipfile
from pathlib import Path


dist_files = [path for path in Path('dist').iterdir() if path.is_file()]
if len(dist_files) != 1:
    raise RuntimeError(f'预期 dist 中只有一个程序，实际为: {dist_files}')

executable = dist_files[0]
release_dir = Path('release')
release_dir.mkdir(exist_ok=True)
archive = release_dir / f'{executable.name}.zip'

info = zipfile.ZipInfo(executable.name)
info.external_attr = (stat.S_IFREG | 0o755) << 16
info.compress_type = zipfile.ZIP_DEFLATED
with zipfile.ZipFile(archive, 'w') as output:
    output.writestr(info, executable.read_bytes())

print(archive)
