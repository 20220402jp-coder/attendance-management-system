"""Built-in clock designs; stable IDs are independent of display names."""
THEMES = {
 'original': dict(name='经典原版', template='clock_original.html', subtitle='最初的打卡页面 · 绿色数字时钟', accent='#39ff14', bg='#121212', mark='✓', label='ORIGINAL EDITION', animation='确认光点'),
 'classic': dict(name='霓虹科幻', template='index.html', subtitle='三维能量环 · 科幻终端', accent='#64f6ed', bg='#102331', mark='◎', label='NEON TERMINAL', animation='能量环确认'),
 'kimono': dict(name='和服卡通', template='clock_kimono.html', subtitle='杏桃和服 · 温柔问候', accent='#c77f95', bg='#fbecf2', mark='✿', label='A LITTLE HELLO', animation='少女鞠躬'),
 'aurora': dict(name='极光漫游', template='clock_collection.html', subtitle='星际光幕 · 流星抵达', accent='#bef8e8', bg='#1c2042', mark='✧', label='INTO THE AURORA', animation='流星划过'),
 'forest': dict(name='森间呼吸', template='clock_collection.html', subtitle='自然绿意 · 新芽生长', accent='#47755a', bg='#e8eddf', mark='♧', label='GROW A LITTLE, EVERY DAY', animation='新芽舒展'),
 'ocean': dict(name='深海蓝调', template='clock_collection.html', subtitle='流动水面 · 涟漪扩散', accent='#5ecfe9', bg='#07354b', mark='≈', label='FIND YOUR OWN RHYTHM', animation='水滴涟漪'),
 'sunrise': dict(name='山间日出', template='clock_collection.html', subtitle='暖橙远山 · 太阳升起', accent='#c96840', bg='#f9e8d2', mark='☀', label='A BRAND NEW DAY', animation='日出光芒'),
 'paper': dict(name='今日票根', template='clock_collection.html', subtitle='纸张质感 · 时间留印', accent='#a54c39', bg='#ede5d6', mark='✳', label='ONE DAY / ONE TICKET', animation='打卡盖章'),
 'arcade': dict(name='像素街机', template='clock_collection.html', subtitle='复古游戏 · 今日通关', accent='#f6ee79', bg='#29203e', mark='+', label='READY PLAYER ONE', animation='金币跳跃'),
 'candy': dict(name='糖果气泡', template='clock_collection.html', subtitle='轻盈软糖 · 彩纸庆祝', accent='#9063c3', bg='#f3e9fc', mark='♡', label='MAKE TODAY A SWEET DAY', animation='彩纸绽放'),
 'mono': dict(name='极简黑白', template='clock_collection.html', subtitle='克制排版 · 一笔确认', accent='#202020', bg='#f0f0ed', mark='↗', label='MAKE IT COUNT.', animation='勾线绘制'),
}
