import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  hydrateNoteImages,
  imagePlaceholderHtml,
  isAssetPlaceholder,
  pdfPlaceholderHtml,
  revokeAllNoteImages,
  sanitizeNoteHtml,
} from '@/utils/note-assets'

/** 在 jsdom 中创建一个隔离 div，返回 { el, append(html) }。 */
function makeEditor() {
  const el = document.createElement('div')
  document.body.appendChild(el)
  return el
}

describe('imagePlaceholderHtml / pdfPlaceholderHtml', () => {
  it('image placeholder has data-asset-id and no src', () => {
    const html = imagePlaceholderHtml(7, 'pic.png')
    expect(html).toContain('data-asset-id="7"')
    expect(html).toContain('alt="pic.png"')
    expect(html).not.toContain('src=')
    expect(html).not.toContain('blob:')
  })

  it('pdf placeholder has data-asset-id and class xuanhuang-asset-link', () => {
    const html = pdfPlaceholderHtml(11, 'doc.pdf')
    expect(html).toContain('data-asset-id="11"')
    expect(html).toContain('xuanhuang-asset-link')
    expect(html).toContain('href="#"')
  })

  it('escapes title HTML to prevent XSS', () => {
    const html = imagePlaceholderHtml(1, '<script>alert(1)</script>')
    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;')
  })
})

describe('sanitizeNoteHtml', () => {
  it('strips blob: src from <img data-asset-id>', () => {
    const raw = `<p>before</p><img data-asset-id="9" src="blob:http://localhost/abc" /><p>after</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).toContain('data-asset-id="9"')
    expect(out).not.toContain('blob:')
    expect(out).not.toMatch(/<img[^>]*src=/)
  })

  it('strips src from <img> without data-asset-id', () => {
    const raw = `<img src="https://example.com/x.png" alt="x" />`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toMatch(/<img[^>]*src=/)
  })

  it('keeps <a class="xuanhuang-asset-link" href="#"> unchanged', () => {
    const raw = `<a href="javascript:alert(1)" data-asset-id="2" class="xuanhuang-asset-link">📄</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).toContain('href="#"')
    expect(out).not.toContain('javascript:')
    expect(out).toContain('data-asset-id="2"')
  })

  it('does not touch text without images', () => {
    const raw = `<p>hello</p><p>world</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).toContain('hello')
    expect(out).toContain('world')
  })
})

describe('hydrateNoteImages', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('injects src for each [data-asset-id] img via fetchBlob', async () => {
    const el = makeEditor()
    el.innerHTML = `
      <img data-asset-id="1" alt="a" />
      <img data-asset-id="2" alt="b" />
      <img src="https://example.com/old.png" />
    `
    const fetchBlob = vi.fn(async (id) => ({
      objectUrl: `blob:http://localhost/${id}`,
      mime: 'image/png',
      blob: new Blob(['x']),
    }))
    const ids = await hydrateNoteImages(el, fetchBlob)
    expect(ids.sort()).toEqual([1, 2])
    expect(fetchBlob).toHaveBeenCalledTimes(2)
    expect(fetchBlob).toHaveBeenCalledWith(1, 'preview')
    expect(fetchBlob).toHaveBeenCalledWith(2, 'preview')
    const imgs = Array.from(el.querySelectorAll('img[data-asset-id]'))
    expect(imgs[0].src).toBe('blob:http://localhost/1')
    expect(imgs[0].dataset.hydrated).toBe('1')
    expect(imgs[1].src).toBe('blob:http://localhost/2')
    expect(imgs[1].dataset.hydrated).toBe('1')
  })

  it('does not re-fetch already hydrated images', async () => {
    const el = makeEditor()
    el.innerHTML = `<img data-asset-id="3" data-hydrated="1" src="blob:prev" />`
    const fetchBlob = vi.fn(async () => ({ objectUrl: 'blob:new' }))
    await hydrateNoteImages(el, fetchBlob)
    expect(fetchBlob).not.toHaveBeenCalled()
  })

  it('leaves img without src when fetchBlob fails (keeps data-asset-id)', async () => {
    const el = makeEditor()
    el.innerHTML = `<img data-asset-id="4" />`
    const fetchBlob = vi.fn(async () => {
      throw new Error('boom')
    })
    await hydrateNoteImages(el, fetchBlob)
    const img = el.querySelector('img[data-asset-id="4"]')
    expect(img.dataset.hydrated).toBeUndefined()
    expect(img.hasAttribute('src')).toBe(false)
  })

  it('returns empty array for null editor', async () => {
    const ids = await hydrateNoteImages(null, async () => ({ objectUrl: 'x' }))
    expect(ids).toEqual([])
  })
})

describe('revokeAllNoteImages', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('revokes blob: src and clears data-hydrated', () => {
    const el = makeEditor()
    el.innerHTML = `<img data-asset-id="5" data-hydrated="1" src="blob:foo" />`
    const revoked = revokeAllNoteImages(el)
    expect(revoked).toBe(1)
    const img = el.querySelector('img')
    expect(img.dataset.hydrated).toBeUndefined()
    expect(img.hasAttribute('src')).toBe(false)
  })

  it('does not touch img without hydrated flag', () => {
    const el = makeEditor()
    el.innerHTML = `<img data-asset-id="6" src="blob:foo" />`
    const revoked = revokeAllNoteImages(el)
    expect(revoked).toBe(0)
    const img = el.querySelector('img')
    expect(img.hasAttribute('src')).toBe(true)
  })

  it('returns 0 for null editor', () => {
    expect(revokeAllNoteImages(null)).toBe(0)
  })
})

describe('isAssetPlaceholder', () => {
  it('returns image info for img[data-asset-id]', () => {
    const el = document.createElement('img')
    el.setAttribute('data-asset-id', '7')
    expect(isAssetPlaceholder(el)).toEqual({ kind: 'image', assetId: 7 })
  })

  it('returns pdf info for a.xuanhuang-asset-link[data-asset-id]', () => {
    const el = document.createElement('a')
    el.className = 'xuanhuang-asset-link'
    el.setAttribute('data-asset-id', '8')
    expect(isAssetPlaceholder(el)).toEqual({ kind: 'pdf', assetId: 8 })
  })

  it('returns null for plain element', () => {
    const el = document.createElement('div')
    expect(isAssetPlaceholder(el)).toBeNull()
  })
})

// =================================================================
// XSS 回归测试
// =================================================================
describe('sanitizeNoteHtml XSS regression', () => {
  it('strips <script> tag and its body entirely', () => {
    const raw = `<p>hello</p><script>alert('xss')</script><p>after</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<script')
    expect(out).not.toContain('alert')
    expect(out).not.toContain('xss')
    // 安全文本应保留
    expect(out).toContain('hello')
    expect(out).toContain('after')
  })

  it('strips <script src=...> remote script', () => {
    const raw = `<script src="https://evil.example.com/x.js"></script>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<script')
    expect(out).not.toContain('evil.example.com')
  })

  it('strips onerror attribute from img', () => {
    const raw = `<img data-asset-id="5" alt="x" onerror="alert(1)" src="x" />`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toMatch(/onerror/i)
    expect(out).not.toContain('alert')
  })

  it('strips onclick attribute on a', () => {
    const raw = `<a href="https://example.com" onclick="alert(1)">click</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toMatch(/onclick/i)
    expect(out).not.toContain('alert')
    // 安全 href 仍保留
    expect(out).toContain('href="https://example.com"')
    expect(out).toContain('click')
  })

  it('strips onload / onmouseover / onfocus attributes', () => {
    const raw = `<p onload="x()" onmouseover="y()" onfocus="z()">hello</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toMatch(/onload/i)
    expect(out).not.toMatch(/onmouseover/i)
    expect(out).not.toMatch(/onfocus/i)
  })

  it('rewrites javascript: href to #', () => {
    const raw = `<a href="javascript:alert(1)">click</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('javascript:')
    expect(out).toContain('href="#"')
  })

  it('rewrites javascript: href with leading whitespace to #', () => {
    const raw = `<a href="   JavaScript:alert(1)">click</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('javascript:')
    expect(out).toContain('href="#"')
  })

  it('rewrites data: href to #', () => {
    const raw = `<a href="data:text/html,<script>alert(1)</script>">click</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('data:text/html')
    expect(out).toContain('href="#"')
  })

  it('rewrites vbscript: href to #', () => {
    const raw = `<a href="vbscript:msgbox(1)">click</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('vbscript:')
    expect(out).toContain('href="#"')
  })

  it('strips <iframe> entirely', () => {
    const raw = `<p>before</p><iframe src="https://evil.example.com/x"></iframe><p>after</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<iframe')
    expect(out).not.toContain('evil.example.com')
    expect(out).toContain('before')
    expect(out).toContain('after')
  })

  it('strips <object> / <embed> tags', () => {
    const raw = `<object data="x.swf"><param name="movie" value="x.swf"></object><embed src="x">`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<object')
    expect(out).not.toContain('<embed')
    expect(out).not.toContain('x.swf')
  })

  it('strips <style> tag and inline style attribute', () => {
    const raw = `<p style="background:url(javascript:alert(1))">x</p><style>body{background:red}</style>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<style')
    expect(out).not.toMatch(/style=/i)
  })

  it('preserves <font color> from foreColor command (persistence)', () => {
    const out = sanitizeNoteHtml(`<font color="#5ce0d8">青</font>`)
    expect(out).toContain('<font color="#5ce0d8">')
  })

  it('preserves safe inline color style and strips unsafe declarations', () => {
    expect(sanitizeNoteHtml(`<span style="color: rgb(92, 224, 216)">x</span>`)).toContain('color: rgb(92, 224, 216)')
    // background-color 也被允许
    expect(sanitizeNoteHtml(`<span style="background-color: #1a2b3c">x</span>`)).toContain('background-color: #1a2b3c')
    // 非纯色声明剥离（url/var 等）
    expect(sanitizeNoteHtml(`<span style="background-image:url(http://evil/x.png)">x</span>`)).not.toContain('background-image')
    expect(sanitizeNoteHtml(`<span style="background:url(javascript:alert(1))">x</span>`)).not.toContain('url(')
    // 非允许属性（如 width / position）被剥离，仅保留颜色（输出被规范化为 "color: #ff0000"）
    expect(sanitizeNoteHtml(`<span style="color:#ff0000; width:999px">x</span>`)).toContain('color: #ff0000')
    expect(sanitizeNoteHtml(`<span style="color:#ff0000; width:999px">x</span>`)).not.toContain('width')
  })

  it('rejects unsafe <font color> values', () => {
    expect(sanitizeNoteHtml(`<font color="javascript:alert(1)">x</font>`)).not.toContain('color=')
    expect(sanitizeNoteHtml(`<font color="url(http://evil)">x</font>`)).not.toContain('color=')
  })

  it('preserves data-asset-id for image and PDF placeholders', () => {
    const raw = imagePlaceholderHtml(33, 'pic.png') + pdfPlaceholderHtml(34, 'doc.pdf')
    const out = sanitizeNoteHtml(raw)
    expect(out).toContain('data-asset-id="33"')
    expect(out).toContain('data-asset-id="34"')
    expect(out).toContain('xuanhuang-asset-link')
  })

  it('allows safe link schemes (http/https/mailto/tel/relative/anchor)', () => {
    const urls = [
      'http://example.com/a',
      'https://example.com/b',
      'mailto:foo@bar.com',
      'tel:+8613800000000',
      '/relative/path',
      '#anchor',
    ]
    for (const u of urls) {
      const out = sanitizeNoteHtml(`<a href="${u}">x</a>`)
      expect(out).toContain(`href="${u}"`)
    }
  })

  it('rejects mixed-case javascript: and tab-prefixed javascript:', () => {
    const raw1 = `<a href="JaVaScRiPt:alert(1)">x</a>`
    expect(sanitizeNoteHtml(raw1)).toContain('href="#"')
    const raw2 = `<a href="\tjavascript:alert(1)">x</a>`
    expect(sanitizeNoteHtml(raw2)).toContain('href="#"')
  })

  it('keeps target=_blank and auto-adds rel=noopener noreferrer', () => {
    const raw = `<a href="https://example.com" target="_blank">x</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).toContain('target="_blank"')
    expect(out).toContain('rel="noopener noreferrer"')
  })

  it('strips xlink:href / formaction / srcdoc attributes', () => {
    const raw = `<a href="https://example.com" xlink:href="javascript:alert(1)" formaction="javascript:alert(1)" srcdoc="<script>alert(1)</script>">x</a>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('xlink:href')
    expect(out).not.toContain('formaction')
    expect(out).not.toContain('srcdoc')
    expect(out).not.toContain('javascript:')
    expect(out).toContain('href="https://example.com"')
  })

  it('strips srcset / xss via img attributes not in whitelist', () => {
    const raw = `<img data-asset-id="1" alt="x" srcset="javascript:alert(1)" />`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('srcset')
    expect(out).not.toContain('javascript:')
  })

  it('removes entire svg subtree (forbidden tag)', () => {
    const raw = `<p>before</p><svg><script>alert(1)</script></svg><p>after</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<svg')
    expect(out).not.toContain('<script')
    expect(out).toContain('before')
    expect(out).toContain('after')
  })

  it('preserves text content of unknown inline tags but drops the tag itself', () => {
    const raw = `<custom-tag>important</custom-tag> text`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<custom-tag')
    expect(out).toContain('important')
    expect(out).toContain('text')
  })

  it('rejects blob: img src on whitelist-tagged img without data-asset-id', () => {
    const raw = `<img src="blob:http://evil/x" alt="x" />`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('blob:')
    expect(out).not.toMatch(/src=/)
  })

  it('case-insensitive script-tag stripping (SCRIPT)', () => {
    const raw = `<SCRIPT>alert(1)</SCRIPT><p>safe</p>`
    const out = sanitizeNoteHtml(raw)
    expect(out.toLowerCase()).not.toContain('<script')
    expect(out).not.toContain('alert')
    expect(out).toContain('safe')
  })

  it('nested iframe + script fully removed', () => {
    const raw = `<iframe srcdoc="<script>alert(1)</script>"><script>alert(2)</script></iframe>`
    const out = sanitizeNoteHtml(raw)
    expect(out).not.toContain('<iframe')
    expect(out).not.toContain('<script')
    expect(out).not.toContain('alert')
  })
})