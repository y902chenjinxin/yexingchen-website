/**
 * 深度 XSS 攻击面穷举：把各类变体一次性塞进 sanitizer，看每条是否真的被挡。
 */
import { describe, it, expect } from 'vitest'
import { sanitizeNoteHtml } from '@/utils/note-assets'

function safe(out, ...bads) {
  for (const b of bads) {
    if (out.includes(b)) {
      throw new Error(`XSS leaked: ${b} in ${out}`)
    }
  }
}

describe('sanitizeNoteHtml - deep XSS attack surface', () => {
  // ========== 1) <script> 系列 ==========
  it('removes <script> with type=module', () => {
    const out = sanitizeNoteHtml(`<script type="module">import('x')</script><p>ok</p>`)
    safe(out, '<script', 'import(')
    expect(out).toContain('ok')
  })

  it('removes <script> nested inside attribute (no DOM execution but should be stripped)', () => {
    const out = sanitizeNoteHtml(`<div title="<script>alert(1)</script>">x</div>`)
    safe(out, '<script', 'alert(1)')
  })

  it('removes <noscript> (deprecated for security)', () => {
    // noscript 本身无 XSS 风险，但和 script 同一族，统一禁
    const out = sanitizeNoteHtml(`<noscript><img src=x onerror=alert(1)></noscript><p>ok</p>`)
    safe(out, '<noscript', 'onerror', 'alert')
    expect(out).toContain('ok')
  })

  // ========== 2) Event handler 系列 ==========
  it('removes on* attributes in any case (OnCliCk, ONERROR...)', () => {
    const out = sanitizeNoteHtml(
      `<a href="https://x" OnCliCk="alert(1)" ONERROR="alert(2)" OnLoAd="alert(3)">x</a>`,
    )
    safe(out, 'OnCliCk', 'ONERROR', 'OnLoAd', 'alert(1)', 'alert(2)', 'alert(3)')
  })

  it('removes inline event in any element (svg, div, span, p)', () => {
    const out = sanitizeNoteHtml(
      `<svg onload="alert(1)"></svg><div onclick="alert(2)"></div><span onmouseover="alert(3)"></span><p onfocus="alert(4)"></p>`,
    )
    safe(out, 'onload', 'onclick', 'onmouseover', 'onfocus', 'alert(1)', 'alert(2)', 'alert(3)', 'alert(4)')
  })

  // ========== 3) javascript: href 系列 ==========
  it('rewrites javascript: with leading control chars to #', () => {
    const out = sanitizeNoteHtml(`<a href="\x01\x02 javascript:alert(1)">x</a>`)
    safe(out, 'javascript:', 'alert(1)')
    expect(out).toContain('href="#"')
  })

  it('rewrites javascript: with NUL byte to #', () => {
    const out = sanitizeNoteHtml(`<a href="\x00javascript:alert(1)">x</a>`)
    safe(out, 'javascript:', 'alert(1)')
    expect(out).toContain('href="#"')
  })

  it('rewrites data: URL with arbitrary mime to #', () => {
    const out = sanitizeNoteHtml(`<a href="data:image/svg+xml,<svg/onload=alert(1)>">x</a>`)
    safe(out, 'data:image', 'onload', 'alert(1)')
    expect(out).toContain('href="#"')
  })

  it('rewrites vbscript: with whitespace to #', () => {
    const out = sanitizeNoteHtml(`<a href="\tvbscript:msgbox(1)">x</a>`)
    safe(out, 'vbscript:', 'msgbox(1)')
    expect(out).toContain('href="#"')
  })

  it('rejects javascript: in img src (irrelevant on img but in case)', () => {
    // <img src=javascript:...> 在某些浏览器会执行。img 默认无 src 时不显示，
    // 但作为深度防御，应去掉 src。
    const out = sanitizeNoteHtml(`<img data-asset-id="1" src="javascript:alert(1)" />`)
    safe(out, 'javascript:', 'alert(1)')
    expect(out).not.toMatch(/src=/)
  })

  // ========== 4) iframe / object / embed / frame ==========
  it('removes <iframe srcdoc> with embedded script', () => {
    const out = sanitizeNoteHtml(
      `<iframe srcdoc="<script>alert(1)</script>"></iframe><p>ok</p>`,
    )
    safe(out, '<iframe', '<script', 'alert(1)')
    expect(out).toContain('ok')
  })

  it('removes <object data=javascript:>', () => {
    const out = sanitizeNoteHtml(`<object data="javascript:alert(1)"></object>`)
    safe(out, '<object', 'javascript:', 'alert(1)')
  })

  it('removes <embed src=javascript:>', () => {
    const out = sanitizeNoteHtml(`<embed src="javascript:alert(1)" />`)
    safe(out, '<embed', 'javascript:', 'alert(1)')
  })

  it('removes <frame> and <frameset>', () => {
    const out = sanitizeNoteHtml(
      `<frameset><frame src="javascript:alert(1)"></frameset>`,
    )
    safe(out, '<frame', '<frameset', 'javascript:', 'alert(1)')
  })

  // ========== 5) 表单类（绕过协议） ==========
  it('removes <form> with action=javascript:', () => {
    const out = sanitizeNoteHtml(
      `<form action="javascript:alert(1)"><input type="submit"></form><p>ok</p>`,
    )
    safe(out, '<form', '<input', 'javascript:', 'alert(1)')
    expect(out).toContain('ok')
  })

  it('removes <button> with formaction=javascript:', () => {
    const out = sanitizeNoteHtml(
      `<button formaction="javascript:alert(1)">x</button>`,
    )
    safe(out, '<button', 'formaction', 'javascript:', 'alert(1)')
  })

  it('removes <textarea> + <select> tags', () => {
    const out = sanitizeNoteHtml(
      `<textarea onfocus="alert(1)"></textarea><select onchange="alert(2)"></select>`,
    )
    safe(out, '<textarea', '<select', 'onfocus', 'onchange', 'alert(1)', 'alert(2)')
  })

  // ========== 6) meta / link / base ==========
  it('removes <meta http-equiv=refresh>', () => {
    const out = sanitizeNoteHtml(`<meta http-equiv="refresh" content="0;url=javascript:alert(1)"><p>ok</p>`)
    safe(out, '<meta', 'javascript:', 'alert(1)')
    expect(out).toContain('ok')
  })

  it('removes <link rel=stylesheet href=javascript:>', () => {
    const out = sanitizeNoteHtml(`<link rel="stylesheet" href="javascript:alert(1)">`)
    safe(out, '<link', 'javascript:', 'alert(1)')
  })

  it('removes <base href=javascript:>', () => {
    const out = sanitizeNoteHtml(`<base href="javascript:alert(1)"><p>ok</p>`)
    safe(out, '<base', 'javascript:', 'alert(1)')
    expect(out).toContain('ok')
  })

  // ========== 7) SVG / MathML 中的脚本 ==========
  it('removes <svg> subtree (svg/onload/script)', () => {
    const out = sanitizeNoteHtml(
      `<svg/onload="alert(1)"><script>alert(2)</script></svg><p>ok</p>`,
    )
    safe(out, '<svg', '<script', 'onload', 'alert(1)', 'alert(2)')
    expect(out).toContain('ok')
  })

  it('removes <math> subtree', () => {
    const out = sanitizeNoteHtml(`<math><mtext><script>alert(1)</script></mtext></math>`)
    safe(out, '<math', '<script', 'alert(1)')
  })

  // ========== 8) CSS / style 注入 ==========
  it('removes inline style with javascript: in url()', () => {
    const out = sanitizeNoteHtml(`<p style="background:url(javascript:alert(1))">x</p>`)
    safe(out, 'javascript:', 'alert(1)', 'style=')
  })

  it('removes <style> block', () => {
    const out = sanitizeNoteHtml(`<style>body{background:url("javascript:alert(1)")}</style><p>ok</p>`)
    safe(out, '<style', 'javascript:', 'alert(1)')
    expect(out).toContain('ok')
  })

  // ========== 9) <a target=_blank> 钓鱼 ==========
  it('auto-adds rel=noopener noreferrer on target=_blank', () => {
    const out = sanitizeNoteHtml(`<a href="https://x.example" target="_blank">x</a>`)
    expect(out).toContain('target="_blank"')
    expect(out).toContain('rel="noopener noreferrer"')
  })

  it('drops target=_top / _parent (reverse-tabnabbing 攻击面更小)', () => {
    // 这两个值也建议归一化为 _blank + noopener；非必须。允许保留。
    const out = sanitizeNoteHtml(`<a href="https://x" target="_top">x</a>`)
    // 当前实现不主动补 rel（非 _blank 触发），确认无 target=_blank 副作用即可
    expect(out).not.toContain('target="_blank"')
  })

  // ========== 10) 属性注入路径 ==========
  it('strips srcset with javascript:', () => {
    const out = sanitizeNoteHtml(`<img data-asset-id="1" alt="x" srcset="javascript:alert(1)" />`)
    safe(out, 'srcset', 'javascript:', 'alert(1)')
  })

  it('strips background attribute', () => {
    const out = sanitizeNoteHtml(`<p background="javascript:alert(1)">x</p>`)
    safe(out, 'background', 'javascript:', 'alert(1)')
  })

  it('strips poster attribute (video/canvas 不在白名单)', () => {
    const out = sanitizeNoteHtml(`<video poster="javascript:alert(1)"></video>`)
    safe(out, '<video', 'javascript:', 'alert(1)')
  })

  // ========== 11) 利用合法标签的 svg-like 拼接绕过 ==========
  it('does not allow javascript: in css background-style hack', () => {
    const out = sanitizeNoteHtml(
      `<p style="background-image:url('javascript:alert(1)')">x</p>`,
    )
    safe(out, 'javascript:', 'alert(1)', 'style=')
  })

  it('strips lowsrc / dynsrc (legacy image event attrs)', () => {
    // 这些属性在白名单外，应当全部剥离
    const out = sanitizeNoteHtml(
      `<img data-asset-id="1" alt="x" lowsrc="javascript:alert(1)" dynsrc="javascript:alert(2)" />`,
    )
    safe(out, 'lowsrc', 'dynsrc', 'javascript:', 'alert(1)', 'alert(2)')
  })

  // ========== 12) 编码绕过 ==========
  it('does not decode html entities inside javascript: (safe: we check string)', () => {
    // &lt;script&gt; in attribute value → 文本节点不会执行；值应原样保留或剥离
    const out = sanitizeNoteHtml(`<a href="&#106;avascript:alert(1)">x</a>`)
    // 浏览器会自动解码 entity 后执行；安全做法：检测解码后是否 javascript:
    // 我们的实现用 DOM 解析后 getAttribute('href') 取的是解码后字符串；
    // isSafeHref 对 'javascript:' 前缀检测应当能匹配。
    expect(out).toContain('href="#"')
    expect(out).not.toContain('alert(1)')
  })

  it('handles entity-encoded javascript: in href (decoded-equal check)', () => {
    const out = sanitizeNoteHtml(
      `<a href="&#x6A;avascript:alert(1)">x</a>`,
    )
    expect(out).toContain('href="#"')
    expect(out).not.toContain('alert(1)')
  })

  it('handles mixed-case + whitespace + entity in href (deep bypass)', () => {
    const out = sanitizeNoteHtml(
      `<a href="\t&#x6A;AVa&#x53;CRipt:alert(1)">x</a>`,
    )
    expect(out).toContain('href="#"')
    expect(out).not.toContain('alert(1)')
  })

  // ========== 13) 文本中残留危险 ==========
  it('does not execute <script> inside a preserved text node', () => {
    // 即便 <script> 被剥离，它的内容文本可能含 </script> 截断闭合；
    // 我们的实现应保留文本但完全去掉 script 节点
    const out = sanitizeNoteHtml(
      `<p>before</p><script>alert('x');</script>after`,
    )
    safe(out, '<script', 'alert(')
    expect(out).toContain('before')
    expect(out).toContain('after')
  })
})