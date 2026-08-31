import { describe, it, expect } from 'vitest'
import {
  pickImageFromClipboard,
  pickAcceptedFromDrop,
  classifyPaste,
  summarizeIgnored,
} from '@/utils/paste-drop'

describe('paste-drop utils', () => {
  describe('pickImageFromClipboard', () => {
    it('returns null when cd is empty', () => {
      expect(pickImageFromClipboard(null)).toBeNull()
      expect(pickImageFromClipboard(undefined)).toBeNull()
    })

    it('picks image from items (DataTransferItemList)', () => {
      const pngFile = { type: 'image/png', name: 'a.png' }
      const cd = {
        items: [
          { kind: 'string', type: 'text/plain' },
          { kind: 'file', type: 'image/png', getAsFile: () => pngFile },
        ],
      }
      expect(pickImageFromClipboard(cd)).toBe(pngFile)
    })

    it('falls back to files when items has no image', () => {
      const pngFile = { type: 'image/png', name: 'b.png' }
      const cd = {
        items: [{ kind: 'string', type: 'text/plain' }],
        files: [{ type: 'text/plain' }, pngFile],
      }
      expect(pickImageFromClipboard(cd)).toBe(pngFile)
    })

    it('ignores non-image files', () => {
      const cd = {
        files: [
          { type: 'application/pdf', name: 'a.pdf' },
          { type: 'text/plain', name: 'b.txt' },
        ],
      }
      expect(pickImageFromClipboard(cd)).toBeNull()
    })

    it('returns null when getAsFile returns null', () => {
      const cd = {
        items: [
          { kind: 'file', type: 'image/png', getAsFile: () => null },
        ],
        files: [],
      }
      expect(pickImageFromClipboard(cd)).toBeNull()
    })
  })

  describe('pickAcceptedFromDrop', () => {
    it('returns [] when dataTransfer is empty', () => {
      expect(pickAcceptedFromDrop(null)).toEqual([])
      expect(pickAcceptedFromDrop({})).toEqual([])
    })

    it('filters image/* and application/pdf', () => {
      const files = [
        { type: 'image/png', name: 'a.png' },
        { type: 'image/jpeg', name: 'b.jpg' },
        { type: 'application/pdf', name: 'c.pdf' },
        { type: 'text/plain', name: 'd.txt' },
        { type: 'application/zip', name: 'e.zip' },
      ]
      const out = pickAcceptedFromDrop({ files })
      expect(out).toHaveLength(3)
      expect(out.map((f) => f.name)).toEqual(['a.png', 'b.jpg', 'c.pdf'])
    })

    it('returns [] when no supported files', () => {
      const files = [{ type: 'text/plain', name: 'a.txt' }]
      expect(pickAcceptedFromDrop({ files })).toEqual([])
    })

    it('mixed list: only image/* and application/pdf pass through', () => {
      const files = [
        { type: 'image/png', name: 'a.png' },
        { type: 'application/pdf', name: 'b.pdf' },
        { type: 'text/plain', name: 'c.txt' },
        { type: 'application/zip', name: 'd.zip' },
        { type: '', name: 'e.bin' }, // 无 MIME 也应被忽略
      ]
      const out = pickAcceptedFromDrop({ files })
      expect(out.map((f) => f.name)).toEqual(['a.png', 'b.pdf'])
    })

    it('FileList-like object works with numeric length', () => {
      const make = (arr) => ({ 0: arr[0], 1: arr[1], 2: arr[2], length: arr.length })
      const fl = make([
        { type: 'image/jpeg', name: 'a.jpg' },
        { type: 'text/plain', name: 'b.txt' },
        { type: 'application/pdf', name: 'c.pdf' },
      ])
      const out = pickAcceptedFromDrop({ files: fl })
      expect(out).toHaveLength(2)
    })
  })

  describe('summarizeIgnored', () => {
    it('returns empty string when files is nullish/empty', () => {
      expect(summarizeIgnored(null)).toBe('')
      expect(summarizeIgnored(undefined)).toBe('')
      expect(summarizeIgnored([])).toBe('')
      expect(summarizeIgnored({})).toBe('')
    })

    it('joins file names with 、', () => {
      const files = [{ name: 'a.txt' }, { name: 'b.zip' }]
      expect(summarizeIgnored(files)).toBe('a.txt、b.zip')
    })

    it('ignores entries without a name', () => {
      const files = [{ name: 'a.txt' }, {}, { name: '' }]
      expect(summarizeIgnored(files)).toBe('a.txt')
    })
  })

  describe('classifyPaste', () => {
    it('classifies image paste', () => {
      const pngFile = { type: 'image/png', name: 'a.png' }
      const cd = {
        items: [{ kind: 'file', type: 'image/png', getAsFile: () => pngFile }],
        getData: () => '',
      }
      const r = classifyPaste(cd)
      expect(r.kind).toBe('image')
      expect(r.file).toBe(pngFile)
    })

    it('classifies text paste', () => {
      const cd = {
        items: [{ kind: 'string', type: 'text/plain' }],
        getData: (t) => (t === 'text/plain' ? 'hello' : ''),
      }
      const r = classifyPaste(cd)
      expect(r.kind).toBe('text')
      expect(r.text).toBe('hello')
    })

    it('falls back to text when no image', () => {
      const cd = {
        getData: (t) => (t === 'text/plain' ? 'plain text' : ''),
      }
      const r = classifyPaste(cd)
      expect(r.kind).toBe('text')
      expect(r.text).toBe('plain text')
    })
  })
})