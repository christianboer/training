"""Minimal Mapbox Vector Tile decoder — enough for Strava's photo tiles."""
import math
import struct


def _varint(b, p):
    r = 0
    s = 0
    while True:
        c = b[p]
        p += 1
        r |= (c & 0x7F) << s
        if not c & 0x80:
            return r, p
        s += 7


def _skip(b, p, wt):
    if wt == 0:
        _, p = _varint(b, p)
    elif wt == 1:
        p += 8
    elif wt == 2:
        n, p = _varint(b, p)
        p += n
    elif wt == 5:
        p += 4
    else:
        raise ValueError(f'wire type {wt}')
    return p


def _value(b, s, e):
    p = s
    v = None
    while p < e:
        k, p = _varint(b, p)
        f, wt = k >> 3, k & 7
        if f == 1 and wt == 2:
            n, p = _varint(b, p)
            v = b[p:p + n].decode('utf-8', 'replace')
            p += n
        elif f == 2 and wt == 5:
            v = struct.unpack_from('<f', b, p)[0]
            p += 4
        elif f == 3 and wt == 1:
            v = struct.unpack_from('<d', b, p)[0]
            p += 8
        elif f in (4, 5) and wt == 0:
            v, p = _varint(b, p)
        elif f == 6 and wt == 0:
            n, p = _varint(b, p)
            v = (n >> 1) ^ -(n & 1)
        elif f == 7 and wt == 0:
            n, p = _varint(b, p)
            v = bool(n)
        else:
            p = _skip(b, p, wt)
    return v


def _points(geom, extent, z, tx, ty):
    """Decode MoveTo/LineTo commands into lat/lon, keeping MoveTo anchors."""
    out = []
    i = 0
    cx = cy = 0
    n = 2 ** z
    while i < len(geom):
        cmd, cnt = geom[i] & 7, geom[i] >> 3
        i += 1
        if cmd in (1, 2):
            for _ in range(cnt):
                dx = (geom[i] >> 1) ^ -(geom[i] & 1)
                i += 1
                dy = (geom[i] >> 1) ^ -(geom[i] & 1)
                i += 1
                cx += dx
                cy += dy
                if cmd == 1:
                    lon = (tx + cx / extent) / n * 360 - 180
                    yy = math.pi - 2 * math.pi * (ty + cy / extent) / n
                    lat = math.degrees(math.atan(math.sinh(yy)))
                    out.append((lat, lon))
        elif cmd == 7:
            pass
        else:
            break
    return out


def decode(data, z, tx, ty):
    """Return [{'layer': name, 'features': [{'props': {...}, 'points': [(lat, lon)]}]}]."""
    b = data
    p = 0
    layer_spans = []
    while p < len(b):
        k, p = _varint(b, p)
        f, wt = k >> 3, k & 7
        if f == 3 and wt == 2:
            n, p = _varint(b, p)
            layer_spans.append((p, p + n))
            p += n
        else:
            p = _skip(b, p, wt)

    layers = []
    for ls, le in layer_spans:
        p = ls
        name = ''
        keys = []
        values = []
        extent = 4096
        feat_spans = []
        while p < le:
            k, p = _varint(b, p)
            f, wt = k >> 3, k & 7
            if f == 1 and wt == 2:
                n, p = _varint(b, p)
                name = b[p:p + n].decode('utf-8', 'replace')
                p += n
            elif f == 3 and wt == 2:
                n, p = _varint(b, p)
                keys.append(b[p:p + n].decode('utf-8', 'replace'))
                p += n
            elif f == 4 and wt == 2:
                n, p = _varint(b, p)
                values.append(_value(b, p, p + n))
                p += n
            elif f == 5 and wt == 0:
                extent, p = _varint(b, p)
            elif f == 2 and wt == 2:
                n, p = _varint(b, p)
                feat_spans.append((p, p + n))
                p += n
            else:
                p = _skip(b, p, wt)

        feats = []
        for fs, fe in feat_spans:
            p = fs
            tags = []
            geom = []
            while p < fe:
                k, p = _varint(b, p)
                f, wt = k >> 3, k & 7
                if f == 2 and wt == 2:
                    n, p = _varint(b, p)
                    end = p + n
                    while p < end:
                        v, p = _varint(b, p)
                        tags.append(v)
                elif f == 4 and wt == 2:
                    n, p = _varint(b, p)
                    end = p + n
                    while p < end:
                        v, p = _varint(b, p)
                        geom.append(v)
                else:
                    p = _skip(b, p, wt)
            props = {}
            for i in range(0, len(tags) - 1, 2):
                if tags[i] < len(keys) and tags[i + 1] < len(values):
                    props[keys[tags[i]]] = values[tags[i + 1]]
            feats.append({'props': props, 'points': _points(geom, extent, z, tx, ty)})
        layers.append({'layer': name, 'features': feats})
    return layers
