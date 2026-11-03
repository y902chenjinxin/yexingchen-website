"""解析 Android 二进制 XML（AXML），输出可读文本（属性里的 @ref 保留为 0x7f...）。"""
import struct
import sys

RES_STRING_POOL = 0x0001
RES_XML_START_NS = 0x0100
RES_XML_END_NS = 0x0101
RES_XML_START_ELEMENT = 0x0102
RES_XML_END_ELEMENT = 0x0103
RES_XML_CDATA = 0x0104
RES_XML_RESOURCE_MAP = 0x0180


def read_string_pool(data, pos, size):
    _t, hsz, csize = struct.unpack('<HHI', data[pos:pos + 8])
    cnt, style_cnt, flags, strings_start, styles_start = struct.unpack('<IIIII', data[pos + 8:pos + 28])
    utf8 = bool(flags & (1 << 8))
    offs = struct.unpack('<%dI' % cnt, data[pos + hsz:pos + hsz + 4 * cnt])
    base = pos + strings_start
    out = []
    for off in offs:
        p = base + off
        if utf8:
            # 长度：1 或 2 字节（高位置 1 表示两字节）
            n = data[p]
            p += 2 if n & 0x80 else 1
            n = data[p]
            if n & 0x80:
                n = ((n & 0x7f) << 8) | data[p + 1]
                p += 2
            else:
                p += 1
            out.append(data[p:p + n].decode('utf-8', 'replace'))
        else:
            n = struct.unpack('<H', data[p:p + 2])[0]
            p += 2
            if n & 0x8000:
                n = ((n & 0x7fff) << 16) | struct.unpack('<H', data[p:p + 2])[0]
                p += 2
            out.append(data[p:p + n * 2].decode('utf-16-le', 'replace'))
    return out


def fmt_value(dtype, data, raw, strings):
    if dtype == 0x01:
        return '@%#010x' % data
    if dtype == 0x03:
        return '"%s"' % (strings[data] if data < len(strings) else raw)
    if dtype == 0x04:
        return repr(struct.unpack('<f', struct.pack('<I', data))[0])
    if dtype == 0x05:
        # complex dimension: 低 8 位单位
        unit = data & 0xFF
        val = data & 0xFFFFFF00
        return '%s(0x%08x)' % ({0: 'px', 1: 'dp', 2: 'sp', 3: 'pt', 4: 'in', 5: 'mm'}.get(unit, '?'), val)
    if dtype == 0x10:
        return str(struct.unpack('<i', struct.pack('<I', data))[0])
    if dtype == 0x11:
        return hex(data)
    if dtype == 0x12:
        return 'true' if data else 'false'
    return str(data)


def parse(path):
    data = open(path, 'rb').read()
    strings = []
    # 先扫一遍字符串池
    pos = 8
    while pos < len(data):
        ctype, chsz, csize = struct.unpack('<HHI', data[pos:pos + 8])
        if csize == 0:
            break
        if ctype == RES_STRING_POOL:
            strings = read_string_pool(data, pos, csize)
            break
        pos += csize

    out = []
    depth = 0
    pos = 8
    while pos < len(data):
        ctype, chsz, csize = struct.unpack('<HHI', data[pos:pos + 8])
        if csize == 0:
            break
        if ctype == RES_XML_START_ELEMENT:
            body = pos + chsz
            _ns, name = struct.unpack('<II', data[body:body + 8])
            a_start, a_size, a_count = struct.unpack('<HHH', data[body + 8:body + 14])
            ap = body + a_start
            attrs = []
            for _ in range(a_count):
                _ans, aname, araw, _vsize, _res0, atype, adata = struct.unpack(
                    '<IIIHBBI', data[ap:ap + 20])
                attrs.append('%s=%s' % (
                    strings[aname] if aname < len(strings) else '?',
                    fmt_value(atype, adata, strings[araw] if araw < len(strings) else '',
                              strings)))
                ap += a_size
            tag = strings[name] if name < len(strings) else '?'
            out.append('%s<%s %s>' % ('  ' * depth, tag, ' '.join(attrs)))
            depth += 1
        elif ctype == RES_XML_END_ELEMENT:
            depth = max(0, depth - 1)
            body = pos + chsz
            _ns, name = struct.unpack('<II', data[body:body + 8])
            out.append('%s</%s>' % ('  ' * depth, strings[name] if name < len(strings) else '?'))
        pos += csize
    return '\n'.join(out)


if __name__ == '__main__':
    print(parse(sys.argv[1]))
