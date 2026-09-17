# -*- coding: utf-8 -*-
"""修正: indices.csv 追加 6 行美股(9/16 行情日)
§3.87 固化: 按字节 ab 追加; assert BOM 在位; 新行行尾与「末行」一致(本文件末行为 LF, 历史 796 行为 CRLF)
⚠️ 禁止 normalize_eol 整表归一化 —— 会导致 1596 行全量 diff(本次已踩, 已 git checkout 还原)
"""
import os

BASE = '/Users/jieyang/Documents/WealthHub'
p = os.path.join(BASE, 'data/processed/history/indices.csv')

with open(p, 'rb') as f:
    d = f.read()
assert d[:3] == b'\xef\xbb\xbf', 'BOM 缺失'
assert d.endswith(b'\n'), '末行无换行'
eol = b'\r\n' if d.endswith(b'\r\n') else b'\n'
print(f'BOM=True 末行EOL={eol!r} size={len(d)} CRLF={d.count(b"\r\n")}')

rows = [
    ['us_index', '2026-09-16', '美股医疗XLV', 'XLV', '167.77', '0.07', '美股收盘'],
    ['us_index', '2026-09-16', '美股医疗IYH', 'IYH', '70.77', '0.18', '美股收盘'],
    ['us_index', '2026-09-16', '纳指100ETF', 'QQQ', '704.72', '0.03', '美股收盘'],
    ['us_index', '2026-09-16', '道指ETF', 'DIA', '515.22', '-1.15', '美股收盘'],
    ['us_index', '2026-09-16', '纳斯达克', '.IXIC', '25978.4238', '-0.01', '美股收盘'],
    ['us_index', '2026-09-16', '标普500', '.INX', '7551.8101', '-0.45', '美股收盘'],
]
with open(p, 'ab') as f:
    for r in rows:
        f.write((','.join(r)).encode('utf-8') + eol)
print(f'indices.csv 追加 {len(rows)} 行 (EOL={eol!r})')
