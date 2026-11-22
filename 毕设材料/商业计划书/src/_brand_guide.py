# -*- coding: utf-8 -*-
"""生成与新图册一致的 Apple 极简品牌规范页 brand_assets/brand_guidelines.html。"""
from pathlib import Path
import _gf_brand as B

OUT = Path(r'F:\GrowthForward_AI学习伴侣\brand_assets\brand_guidelines.html')

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#F5F5F7;color:#1D1D1F;
 font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
 -webkit-font-smoothing:antialiased;line-height:1.65}
.wrap{max-width:1000px;margin:0 auto;padding:56px 32px 80px}
header{background:#fff;border:1px solid #E5E5EA;border-radius:20px;padding:38px 40px;
 box-shadow:0 2px 18px rgba(0,0,0,.035);display:flex;align-items:center;gap:26px}
header .mk{width:78px;height:78px;flex:0 0 auto}
header .mk svg{width:100%;height:100%}
h1{font-size:30px;font-weight:600;letter-spacing:-.6px;margin:0 0 6px}
.sub{color:#6E6E73;font-size:14px;letter-spacing:.4px}
.tag{display:inline-block;background:#EAF3FF;color:#0071E3;border-radius:999px;
 padding:4px 12px;font-size:12px;font-weight:600;margin-top:12px}
section{background:#fff;border:1px solid #E5E5EA;border-radius:20px;padding:30px 34px;margin-top:20px;
 box-shadow:0 2px 18px rgba(0,0,0,.03)}
h2{font-size:17px;font-weight:600;margin:0 0 4px;letter-spacing:.2px}
.en{font-size:11px;color:#86868B;letter-spacing:1.3px;text-transform:uppercase;margin-bottom:22px}
p{font-size:13.5px;color:#3A3A3C;margin:8px 0}
.grid{display:grid;gap:14px}
.g6{grid-template-columns:repeat(6,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}
.sw{border:1px solid #E5E5EA;border-radius:14px;padding:12px}
.chip{height:56px;border-radius:10px;margin-bottom:12px}
.nm{font-size:12.5px;font-weight:600}
.hx{font-size:11.5px;color:#0071E3;margin-top:2px}
.use{font-size:11.5px;color:#86868B;margin-top:6px}
.card{background:#FAFAFC;border:1px solid #EDEDEF;border-radius:14px;padding:20px;text-align:center}
.card svg{width:100%;max-width:150px;height:auto}
.cap{font-size:12px;color:#6E6E73;margin-top:12px}
.logoRow{display:flex;align-items:center;gap:18px;background:#FAFAFC;border:1px solid #EDEDEF;
 border-radius:14px;padding:22px 26px}
.logoRow .m{width:88px;height:88px;flex:0 0 auto}
.logoRow .m svg{width:100%;height:100%}
.logoRow .nm2{font-size:30px;font-weight:600;letter-spacing:-.8px}
.logoRow .nm2 span{color:#0071E3}
.logoRow .sb{font-size:12px;color:#86868B;letter-spacing:1.4px;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#86868B;font-weight:500;font-size:11.5px;letter-spacing:.6px;
 border-bottom:1px solid #D2D2D7;padding:10px 8px}
td{border-bottom:1px solid #EDEDEF;padding:12px 8px;color:#3A3A3C;vertical-align:top}
td b{color:#0071E3;font-weight:600}
ul{margin:8px 0;padding-left:20px;font-size:13.5px;color:#3A3A3C}
li{margin:5px 0}
footer{color:#86868B;font-size:12px;text-align:center;margin-top:28px;line-height:1.9}
.hl{color:#0071E3;font-weight:600}
"""


def sec(title, en, body):
    return f'<section><h2>{title}</h2><div class="en">{en}</div>{body}</section>'


def build():
    sw = ''.join(
        f'<div class="sw"><div class="chip" style="background:{c}"></div>'
        f'<div class="nm">{n}</div><div class="hx">{c}</div>'
        f'<div class="use">{u}</div></div>'
        for (n, c, u) in [(x[0], x[1], x[2]) for x in B.PALETTE]
    )
    uses = ['正文与主标题 · 屏幕脸', '主色 · 表头 · 图形标', '浅底 · 选中态 · 数据带',
            '页面底 · 次级卡', '边框 · 分隔线', '向前箭头 · 唯一点睛']

    pal = ''.join(
        f'<div class="sw"><div class="chip" style="background:{c}"></div>'
        f'<div class="nm">{n}</div><div class="hx">{c}</div>'
        f'<div class="use">{uses[i]}</div></div>'
        for i, (n, c, _) in enumerate(B.PALETTE))

    logos = ''.join(
        f'<div class="card"><div style="max-width:{w}px;margin:0 auto">{B.icon("ic"+str(i))}</div>'
        f'<div class="cap">{t}</div></div>'
        for i, (w, t) in enumerate([(150, 'App Icon · 主用'), (110, '中等尺寸'), (72, '最小 16 px 可辨识')]))

    o = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>GrowthForward · 品牌视觉规范</title>', f'<style>{CSS}</style></head><body><div class="wrap">']
    o.append(f'''<header><div class="mk">{B.mark()}</div><div>
      <h1>GrowthForward 品牌视觉规范</h1>
      <div class="sub">成长向前 · AI 学习伴侣　|　Brand Identity Guidelines</div>
      <div class="tag">Apple 极简体系 · V3 · 2026-11-16</div></div></header>''')

    o.append(sec('01　色彩系统', 'Color System',
                 f'<div class="grid g6">{pal}</div>'
                 f'<p>整套视觉只有<span class="hl">一种主色（前进蓝 #0071E3）</span>与'
                 f'<span class="hl">一种点睛色（火花橙 #FF9F0A）</span>；其余全部交给白、石墨与灰阶。'
                 f'风险 / 异常单独使用砖红 {B.RISK}，不引入第三种彩色，保证 A4 黑白打印仍可读。</p>'))

    o.append(sec('02　图形标构造', 'Logo Construction',
                 f'''<div class="logoRow"><div class="m">{B.mark()}</div><div>
                   <div class="nm2">Growth<span>Forward</span></div>
                   <div class="sb">成长向前 · AI 学习伴侣</div></div></div>
                 <div class="grid g3" style="margin-top:14px">
                   <div class="card"><p><b>开口圆环</b><br/>可延展、可复用的学习闭环</p></div>
                   <div class="card"><p><b>冲出开口的箭头</b><br/>持续向前，唯一暖色</p></div>
                   <div class="card"><p><b>环内短横</b><br/>G 的字骨，也是每日基线</p></div>
                 </div>
                 <p>图形标为纯几何单线，无渐变、无描边装饰、无拟物高光；最小使用尺寸 16 px。
                 字标用无衬线字族，标题字重 600，字距 −0.5 pt。</p>'''))

    o.append(sec('03　App Icon', 'Application Icon',
                 f'<div class="grid g3">{logos}</div>'
                 '<p>圆角方形（23% 圆角）+ 蓝色渐变 + 单色 G 标；箭头使用浅火花橙，'
                 '在深色底上保持辨识度。不使用阴影、光泽或拟物材质。</p>'))

    o.append(sec('04　吉祥物「小前」', 'Mascot',
                 f'''<div class="grid g2">
                   <div class="card" style="padding:8px">{B.mascot("gm")}
                     <div class="cap">小前 Qian · 极简悬浮机器人</div></div>
                   <div><ul>
                     <li>圆角头 120×116、圆角 38，白到云雾的极淡渐变 + 柔和落影</li>
                     <li>深墨屏幕脸，只有两个白色光点与一条微笑弧</li>
                     <li>银色天线 + 火花橙光点，是全形象唯一的彩色</li>
                     <li>前进蓝 9% 椭圆投影，表达「轻量、安静、不打扰」</li>
                     <li>去掉腮红、渐变高光与装饰星；24 px 下仍可辨识</li>
                   </ul></div></div>'''))

    o.append(sec('05　字体与图形规范', 'Typography and Grid',
                 '''<table><tr><th>项目</th><th>规范</th><th>理由</th></tr>
                 <tr><td><b>字族</b></td><td>SF Pro / 苹方 / 微软雅黑 / Noto Sans CJK，全册无衬线</td><td>屏幕与投影都清晰，风格统一</td></tr>
                 <tr><td><b>字重</b></td><td>标题 600 · 正文 400 · 弱化信息 400 + 灰阶</td><td>层级靠字号灰度，不靠彩色块</td></tr>
                 <tr><td><b>圆角</b></td><td>卡片 14 px · icon 23% · 胶囊全圆</td><td>柔和、无锐角压迫感</td></tr>
                 <tr><td><b>线条</b></td><td>0.5–1 px 银线 #D2D2D7，禁止粗黑框与双线装饰</td><td>轻量化分隔</td></tr>
                 <tr><td><b>网格</b></td><td>8 pt 基准；图幅 680×960；内容区 632 全宽</td><td>40 张图与 54 页册页严格对齐</td></tr>
                 <tr><td><b>留白</b></td><td>页边距左右 12 / 上 10 / 下 8 mm</td><td>A4 印刷与答辩投影一致</td></tr></table>'''))

    o.append(sec('06　应用矩阵', 'Applications',
                 '''<div class="grid g3">
                   <div class="card"><p><b>页眉微标</b><br/>10 px 图形标 + 书名，54 页统一</p></div>
                   <div class="card"><p><b>扉页 / 图页水印</b><br/>大号 G 标 4% 透明度</p></div>
                   <div class="card"><p><b>封面封底</b><br/>白纸底 + 大标题 + 极简「小前」</p></div>
                   <div class="card"><p><b>图表强调</b><br/>前进蓝表头 / 冰蓝浅底 / 砖红风险</p></div>
                   <div class="card"><p><b>App Icon</b><br/>桌面与小程序入口</p></div>
                   <div class="card"><p><b>色卡与规范页</b><br/>本页、图 0-1、封面、封底</p></div>
                 </div>'''))

    o.append('<footer>GrowthForward · 成长向前 AI 学习伴侣　|　Learn. Grow. Keep Moving Forward.<br/>'
             '本规范与《商业计划书学术图表册》V3（2026-11-16）一致；历史暖橙素材见 legacy/ 目录。</footer>')
    o.append('</div></body></html>')
    return '\n'.join(o)


if __name__ == '__main__':
    OUT.write_text(build(), encoding='utf-8')
    print('wrote', OUT)
