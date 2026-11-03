"""解析 resources.arsc：把 0x7fTTEEEE 解析成 type 名 + 值（字符串/颜色/尺寸/文件路径）。"""
import struct
import sys

RES_TABLE_TYPE = 0x0002
RES_STRING_POOL = 0x0001
RES_TABLE_PACKAGE = 0x0200
RES_TABLE_TYPE_SPEC = 0x0202
RES_TABLE_TYPE = 0x0201


def read_pool(data, pos):
    _t, hsz, csize = struct.unpack('<HHI', data[pos:pos + 8])
    cnt, style_cnt, flags, strings_start, _ss = struct.unpack('<IIIII', data[pos + 8:pos + 28])
    utf8 = bool(flags & (1 << 8))
    offs = struct.unpack('<%dI' % cnt, data[pos + hsz:pos + hsz + 4 * cnt])
    base = pos + strings_start
    out = []
    for off in offs:
        p = base + off
        if utf8:
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


def fmt(dtype, data, strings):
    if dtype == 0x01:
        return '@ref'
    if dtype == 0x03:
        return strings[data] if data < len(strings) else '?'
    if dtype == 0x04:
        return '%g' % struct.unpack('<f', struct.pack('<I', data))[0]
    if dtype == 0x05:
        mant = data >> 8
        unit = data & 0xf
        return '%d%s' % (mant, {0: 'px', 1: 'dp', 2: 'sp', 3: 'pt'}.get(unit, '?'))
    if dtype == 0x10:
        return str(struct.unpack('<i', struct.pack('<I', data))[0])
    if dtype == 0x11:
        return '#%08X' % data
    if dtype == 0x12:
        return 'true' if data else 'false'
    if dtype == 0x1c:
        return '#%08X' % data
    return str(data)


def parse(path):
    data = open(path, 'rb').read()
    _t, hsz, total = struct.unpack('<HHI', data[0:8])
    pos = hsz
    strings = []
    packages = []
    while pos < total:
        ctype, chsz, csize = struct.unpack('<HHI', data[pos:pos + 8])
        if csize <= 0:
            break
        if ctype == RES_STRING_POOL:
            strings = read_pool(data, pos)
        elif ctype == RES_TABLE_PACKAGE:
            pkg_id = struct.unpack('<I', data[pos + 8:pos + 12])[0]
            name = data[pos + 12:pos + 12 + 256].decode('utf-16-le', 'replace').split('\x00')[0]
            type_off = struct.unpack('<I', data[pos + 12 + 256 + 4 + 4 + 4:pos + 12 + 256 + 4 + 4 + 4 + 4])[0]
            # typeStrings 偏移在 header 里
            type_strings_off, _last, key_strings_off = struct.unpack(
                '<III', data[pos + 268:pos + 280])
            type_names = read_pool(data, pos + type_strings_off)
            # 逐个 type chunk
            p = pos + 12 + 256 + 8 + 4 + 4 + 4 + 4 + 4 + 4 + 4
            # 简单做法：从 headerSize 之后遍历
            start = pos + chsz
            tp = start
            while tp < pos + csize:
                t2, h2, s2 = struct.unpack('<HHI', data[tp:tp + 8])
                if s2 <= 0:
                    break
                if t2 == RES_TABLE_TYPE:
                    tid = data[tp + 8]
                    flags = data[tp + 9]
                    entry_count, entries_start = struct.unpack('<II', data[tp + 12:tp + 20])
                    tname = type_names[tid - 1] if 0 < tid <= len(type_names) else '?'
                    offs = struct.unpack('<%dI' % entry_count, data[tp + h2:tp + h2 + 4 * entry_count])
                    base = tp + entries_start
                    for i, o in enumerate(offs):
                        if o == 0xFFFFFFFF:
                            continue
                        ep = base + o
                        esize, eflags = struct.unpack('<HH', data[ep:ep + 4])
                        val = ep + esize
                        vsize, res0, dtype, vdata = struct.unpack('<HBBI', data[val:val + 8])
                        packages.append((tid, i, tname, dtype, vdata))
                tp += s2
        pos += csize
    return strings, packages


if __name__ == '__main__':
    strings, pkgs = parse(sys.argv[1])
    want = sys.argv[2] if len(sys.argv) > 2 else None
    for tid, i, tname, dtype, vdata in pkgs:
        rid = '0x7f%02x%04x' % (tid, i)
        if want and want not in tname:
            continue
        if tname in ('id', 'attr', 'style', 'styleable', 'anim', 'animator', 'interpolator',
                     'xml', 'raw', 'color', 'dimen', 'string', 'drawable', 'layout', 'mipmap'):
            print('%-12s %-10s %-10s %s' % (rid, tname, str(i), fmt(dtype, vdata, strings)))
