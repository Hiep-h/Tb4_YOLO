#!/usr/bin/env python3
import os
import re
import statistics
import sys

LINE_RE = re.compile(r'^\[(?P<proc>[^\]]+)\] \[(?P<level>[A-Z]+)\] \[(?P<ts>[0-9.]+)\] \[(?P<node>[^\]]+)\]: (?P<msg>.*)$')
FRAME_RE = re.compile(r'^khung (\d+) \(([0-9.]+) ms\): (.*)$')
GOAL_START_RE = re.compile(r'^(Goal \d+): \(')
GOAL_RESULT_RE = re.compile(r'^(Goal \d+): (THANH CONG|BI HUY|THAT BAI|KHONG RO)$')
DET_RE = re.compile(r'^(.*) ([0-9.]+)$')
NO_OBJECT = 'khong thay vat the'


def parse_log(path):
    frames = []
    goal_starts = []
    goal_results = []
    with open(path) as f:
        for raw in f:
            raw = raw.rstrip('\n')
            m = LINE_RE.match(raw)
            if not m:
                continue
            ts = float(m.group('ts'))
            node = m.group('node')
            msg = m.group('msg')
            if node == 'yolo_detector':
                fm = FRAME_RE.match(msg)
                if not fm:
                    continue
                idx, ms, rest = int(fm.group(1)), float(fm.group(2)), fm.group(3)
                dets = []
                if rest != NO_OBJECT:
                    for item in rest.split(', '):
                        dm = DET_RE.match(item)
                        if dm:
                            dets.append((dm.group(1), float(dm.group(2))))
                frames.append({'ts': ts, 'idx': idx, 'ms': ms, 'dets': dets, 'raw': raw})
            elif node == 'goal_navigator':
                gm = GOAL_START_RE.match(msg)
                if gm:
                    goal_starts.append((ts, gm.group(1)))
                    continue
                rm = GOAL_RESULT_RE.match(msg)
                if rm:
                    goal_results.append((ts, rm.group(1), rm.group(2)))
    return frames, goal_starts, goal_results


def segment_for(ts, goal_starts):
    name = 'truoc khi di'
    for start_ts, goal_name in goal_starts:
        if ts >= start_ts:
            name = goal_name
        else:
            break
    return name


def build_report(frames, goal_starts, goal_results):
    lines = []
    total = len(frames)
    no_obj = sum(1 for fr in frames if not fr['dets'])
    times = [fr['ms'] for fr in frames]
    mean_t = statistics.mean(times) if times else 0.0
    median_t = statistics.median(times) if times else 0.0

    lines.append('# Tong ket YOLO')
    lines.append('')
    lines.append('- Tong so khung: %d' % total)
    lines.append('- Khung khong thay vat the: %d' % no_obj)
    lines.append('- Thoi gian suy luan trung binh: %.1f ms' % mean_t)
    lines.append('- Thoi gian suy luan trung vi: %.1f ms' % median_t)
    lines.append('')

    by_class = {}
    for fr in frames:
        for name, conf in fr['dets']:
            s = by_class.setdefault(name, {'count': 0, 'best': 0.0, 'sum': 0.0})
            s['count'] += 1
            s['best'] = max(s['best'], conf)
            s['sum'] += conf

    lines.append('## Theo lop vat the')
    lines.append('')
    lines.append('| Lop | So khung | Conf cao nhat | Conf trung binh |')
    lines.append('|---|---|---|---|')
    for name, s in sorted(by_class.items(), key=lambda kv: -kv[1]['best']):
        avg = s['sum'] / s['count'] if s['count'] else 0.0
        lines.append('| %s | %d | %.2f | %.2f |' % (name, s['count'], s['best'], avg))
    lines.append('')

    by_seg = {}
    seg_order = ['truoc khi di'] + [name for _, name in goal_starts]
    for fr in frames:
        seg = segment_for(fr['ts'], goal_starts)
        s = by_seg.setdefault(seg, {'count': 0, 'no_obj': 0, 'times': []})
        s['count'] += 1
        s['times'].append(fr['ms'])
        if not fr['dets']:
            s['no_obj'] += 1

    lines.append('## Theo doan duong giua cac goal')
    lines.append('')
    lines.append('| Doan | So khung | Khong thay vat | Thoi gian TB (ms) |')
    lines.append('|---|---|---|---|')
    for seg in seg_order:
        s = by_seg.get(seg)
        if not s:
            continue
        avg = statistics.mean(s['times']) if s['times'] else 0.0
        lines.append('| %s | %d | %d | %.1f |' % (seg, s['count'], s['no_obj'], avg))
    lines.append('')

    if goal_results:
        lines.append('## Ket qua tung goal')
        lines.append('')
        lines.append('| Goal | Ket qua |')
        lines.append('|---|---|')
        for _, name, status in goal_results:
            lines.append('| %s | %s |' % (name, status))
        lines.append('')

    samples = []
    for fr in frames:
        for name, conf in fr['dets']:
            samples.append((conf, fr['raw']))
    samples.sort(key=lambda t: -t[0])
    seen_raw = set()
    top_raw = []
    for conf, raw in samples:
        if raw in seen_raw:
            continue
        seen_raw.add(raw)
        top_raw.append(raw)
        if len(top_raw) >= 8:
            break

    lines.append('## 8 dong log mau co do tin cay cao')
    lines.append('')
    for raw in top_raw:
        lines.append('    %s' % raw)
    lines.append('')

    return '\n'.join(lines)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/lab05_launch.log')
    if not os.path.exists(path):
        print('Khong tim thay file log: %s' % path)
        return 1
    frames, goal_starts, goal_results = parse_log(path)
    report = build_report(frames, goal_starts, goal_results)
    print(report)
    out_path = os.path.expanduser('~/yolo_summary.md')
    with open(out_path, 'w') as f:
        f.write(report + '\n')
    print('\nDa ghi %s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
