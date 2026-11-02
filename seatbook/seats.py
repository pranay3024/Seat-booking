"""
Seat layout, transcribed from the venue floor plan.

Each row has 4 blocks (left → right as seen from the hall, stage at the top),
separated by aisles. Each block is (first_seat, last_seat), inclusive.

If any row in your real hall differs, just edit the numbers here —
the seat map, validation and totals all update automatically.
"""

STALLS = [
    ("A", [(1, 7), (8, 14), (15, 21), (22, 28)]),
    ("B", [(1, 8), (9, 16), (17, 24), (25, 32)]),
    ("C", [(1, 8), (9, 16), (17, 24), (25, 32)]),
    ("D", [(1, 8), (9, 17), (18, 25), (26, 33)]),
    ("E", [(1, 9), (10, 18), (19, 27), (28, 36)]),
    ("F", [(1, 9), (10, 18), (19, 27), (28, 36)]),
    ("G", [(1, 10), (11, 20), (21, 29), (30, 39)]),
    ("H", [(1, 10), (11, 20), (21, 30), (31, 40)]),
    ("I", [(1, 11), (12, 21), (22, 31), (32, 42)]),
    ("J", [(1, 11), (12, 21), (22, 31), (32, 42)]),
    ("K", [(1, 11), (12, 22), (23, 32), (33, 43)]),
    ("L", [(1, 12), (13, 23), (24, 34), (35, 46)]),
    ("M", [(1, 12), (13, 23), (24, 34), (35, 46)]),
    ("N", [(1, 12), (13, 24), (25, 35), (36, 47)]),
    ("O", [(1, 13), (14, 25), (26, 37), (38, 50)]),
    ("P", [(1, 13), (14, 25), (26, 37), (38, 50)]),
    ("Q", [(1, 13), (14, 26), (27, 38), (39, 51)]),
    ("R", [(1, 13), (14, 25), (26, 37), (38, 50)]),
]

BALCONY = [
    ("S", [(1, 13), (14, 25), (26, 37), (38, 50)]),
    ("T", [(1, 13), (14, 25), (26, 37), (38, 50)]),
    ("U", [(1, 13), (14, 26), (27, 39), (40, 52)]),
    ("V", [(1, 14), (15, 27), (28, 40), (41, 54)]),
    ("W", [(1, 13), (14, 26), (27, 39), (40, 52)]),
]

SECTIONS = [
    ("stalls", "Stalls", STALLS),
    ("balcony", "Balcony", BALCONY),
]


def _build():
    layout, section_of, row_index = [], {}, {}
    idx = 0
    for key, name, rows in SECTIONS:
        sec_rows, count = [], 0
        for row, blocks in rows:
            row_index[row] = idx
            idx += 1
            seat_blocks = []
            for start, end in blocks:
                nums = list(range(start, end + 1))
                seat_blocks.append(nums)
                for n in nums:
                    section_of[f"{row}{n}"] = key
                count += len(nums)
            sec_rows.append({"row": row, "blocks": seat_blocks})
        layout.append({"key": key, "name": name, "rows": sec_rows, "count": count})
    return layout, section_of, row_index


LAYOUT, SECTION_OF, ROW_INDEX = _build()
ALL_SEATS = frozenset(SECTION_OF)
TOTAL_SEATS = len(ALL_SEATS)
SECTION_COUNTS = {s["key"]: s["count"] for s in LAYOUT}


def seat_sort_key(label: str):
    return (ROW_INDEX.get(label[:1], 99), int(label[1:]) if label[1:].isdigit() else 0)


def group_by_row(labels):
    """['A5','A6','B2'] -> [('A', [5, 6]), ('B', [2])]"""
    out = {}
    for lab in sorted(labels, key=seat_sort_key):
        out.setdefault(lab[0], []).append(int(lab[1:]))
    return list(out.items())
