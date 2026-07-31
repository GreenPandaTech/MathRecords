# OEIS submission pack

Generated from the evidence files, not typed. Every certificate, timing and
DATA line below was read out of the JSON the computation wrote.

**4 term(s) ready to submit.**

## Do this first, every time

Run `python verify_all.py` here. It must exit 0. If it does not, a claim has
drifted from its evidence and nothing should be submitted until it passes.

Registration is already done, so there is no waiting period any more.

## Order to submit

Ranked by evidence actually on disk, strongest first:

* **A217058** a(12)=57 — 3 confirmed refutation path(s), lower bound found by search
* **A217236** a(4)=84 — 3 confirmed refutation path(s), lower bound found by search
* **A217005** a(19)=52 — 3 confirmed refutation path(s), lower bound from the free construction
* **A217007** a(7)=68 — 3 confirmed refutation path(s), lower bound from the free construction

**Submit A217058 first, and alone**, then wait for it to be ACCEPTED before
sending the next. One round-trip teaches more than any amount of preparation,
and a question about your strongest result is better answered once than five
times. `A217058` was submitted on Jul 30 2026 and is under review.

## Never

* Submit a term whose cross-check does not say AGREES.
* Retype a certificate. Copy it. A single wrong character is a retraction.
* Claim a term whose family gate did not reproduce the published value.
* Alter or delete a line already in EXTENSIONS. Add yours below the existing ones.
* Write British spellings in a submission: the OEIS uses US English (color,
  relabeling). The comments below are already US-spelled.
* Let a comment grow. The editors asked for brevity and for every technical term
  to be defined before use, since the entry itself never mentions partitions or
  arithmetic progressions. If in doubt, submit DATA and EXTENSIONS with no comment
  at all — an editor explicitly offered that.

---

## A217058 — a(12) = 57

Page: https://oeis.org/A217058  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which has no reversal-symmetry constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine. (Both engines break the standard colour-permutation symmetry, which is textbook and independent of that work.)

### 1. DATA
```
18,21,25,29,33,36,40,42,45,48,52,55,57
```

### 2. b-file — nothing to upload
`A217058` has no uploaded b-file, so the OEIS generates one from DATA and the new term appears there by itself. `b217058.txt` (13 rows, 0 to 12) is in this repository if an editor ever asks for one.

### 3. EXTENSIONS — ADD this line; never alter the lines already there
```
a(12) from _Leo Y. Zhang_, Aug 01 2026
```

### 4. COMMENT — paste verbatim, including the wrapper lines
```
From _Leo Y. Zhang_, Aug 01 2026: (Start)
a(12) = 57 was computed with a SAT solver.

Written out, a(12) is the least n such that every partition of [1,n] into 12+2 classes contains two elements in one of the first 12 classes, a 3-term arithmetic progression in the next, or a 4-term one in the last.

The following partition of [1,56] has none of those, so a(12) > 56. Each "." is one of the 12 classes that must stay a singleton, and 1 and 2 mark the two remaining classes (no 3-term AP in the class marked 1 and no 4-term AP in the class marked 2):

2.21221212.12.22211.112.2221.222.2.1..12221211212..22212

That no such partition of [1,57] exists was confirmed by a second, independent encoding. The partition above was found by search.
(End)
```

*Evidence behind the two sentences above, kept out of the comment because the editors asked for brevity: refutation 6257 s, all 75 cubes; witness 3926 s; free construction alone would give only a(12) >= 56. The family gate reproduced the published a(11) = 55 before this term was claimed (probe_gate_a11_sat.json + probe_gate_a11_unsat.json).*

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "2.21221212.12.22211.112.2221.222.2.1..12221211212..22212" 12 3 4
```

## A217236 — a(4) = 84

Page: https://oeis.org/A217236  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which has no reversal-symmetry constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine. (Both engines break the standard colour-permutation symmetry, which is textbook and independent of that work.)

### 1. DATA
```
55,71,75,79,84
```

### 2. b-file — nothing to upload
`A217236` has no uploaded b-file, so the OEIS generates one from DATA and the new term appears there by itself. `b217236.txt` (5 rows, 0 to 4) is in this repository if an editor ever asks for one.

### 3. EXTENSIONS — ADD this line; never alter the lines already there
```
a(4) from _Leo Y. Zhang_, Aug 01 2026
```

### 4. COMMENT — paste verbatim, including the wrapper lines
```
From _Leo Y. Zhang_, Aug 01 2026: (Start)
a(4) = 84 was computed with a SAT solver.

Written out, a(4) is the least n such that every partition of [1,n] into 4+2 classes contains two elements in one of the first 4 classes, a 4-term arithmetic progression in the next, or a 5-term one in the last.

The following partition of [1,83] has none of those, so a(4) > 83. Each "." is one of the 4 classes that must stay a singleton, and 1 and 2 mark the two remaining classes (no 4-term AP in the class marked 1 and no 5-term AP in the class marked 2):

122121221221212221.212121221121222211121.221212222.2222.212211211122221211122212122

That no such partition of [1,84] exists was confirmed by a second, independent encoding. The partition above was found by search.
(End)
```

*Evidence behind the two sentences above, kept out of the comment because the editors asked for brevity: refutation 7965 s, all 80 cubes; witness 6470 s; free construction alone would give only a(4) >= 80. The family gate reproduced the published a(3) = 79 before this term was claimed (probe_A217236_gate_sat_n78.json + probe_A217236_gate_unsat_n79.json).*

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "122121221221212221.212121221121222211121.221212222.2222.212211211122221211122212122" 4 4 5
```

## A217005 — a(19) = 52

Page: https://oeis.org/A217005  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which has no reversal-symmetry constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine. (Both engines break the standard colour-permutation symmetry, which is textbook and independent of that work.)

### 1. DATA
```
9,14,17,20,21,24,25,28,31,33,35,37,39,42,44,46,48,50,51,52
```

### 2. b-file — nothing to upload
`A217005` has no uploaded b-file, so the OEIS generates one from DATA and the new term appears there by itself. `b217005.txt` (20 rows, 0 to 19) is in this repository if an editor ever asks for one.

### 3. EXTENSIONS — ADD this line; never alter the lines already there
```
a(19) from _Leo Y. Zhang_, Aug 01 2026
```

### 4. COMMENT — paste verbatim, including the wrapper lines
```
From _Leo Y. Zhang_, Aug 01 2026: (Start)
a(19) = 52 was computed with a SAT solver.

Written out, a(19) is the least n such that every partition of [1,n] into 19+2 classes contains two elements in one of the first 19 classes, or a 3-term arithmetic progression in either of the last two.

The following partition of [1,51] has none of those, so a(19) > 51. Each "." is one of the 19 classes that must stay a singleton, and 1 and 2 mark the two remaining classes (neither of them contains a 3-term AP):

..11.1122.2211.1122.22.........11.1122.2211.1122.22

That no such partition of [1,52] exists was confirmed by a second, independent encoding. The partition above is the previous term's with one more singleton, so the content of this term is the upper bound.
(End)
```

*Evidence behind the two sentences above, kept out of the comment because the editors asked for brevity: refutation 4507 s, all 36 cubes; witness 1520 s; free construction alone would give only a(19) >= 52. The family gate reproduced the published a(18) = 51 before this term was claimed (validate_gate05.json).*

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "..11.1122.2211.1122.22.........11.1122.2211.1122.22" 19 3 3
```

## A217007 — a(7) = 68

Page: https://oeis.org/A217007  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which has no reversal-symmetry constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine. (Both engines break the standard colour-permutation symmetry, which is textbook and independent of that work.)

### 1. DATA
```
35,40,53,54,56,66,67,68
```

### 2. b-file — nothing to upload
`A217007` has no uploaded b-file, so the OEIS generates one from DATA and the new term appears there by itself. `b217007.txt` (8 rows, 0 to 7) is in this repository if an editor ever asks for one.

### 3. EXTENSIONS — ADD this line; never alter the lines already there
```
a(7) from _Leo Y. Zhang_, Aug 01 2026
```

### 4. COMMENT — paste verbatim, including the wrapper lines
```
From _Leo Y. Zhang_, Aug 01 2026: (Start)
a(7) = 68 was computed with a SAT solver.

Written out, a(7) is the least n such that every partition of [1,n] into 7+2 classes contains two elements in one of the first 7 classes, or a 4-term arithmetic progression in either of the last two.

The following partition of [1,67] has none of those, so a(7) > 67. Each "." is one of the 7 classes that must stay a singleton, and 1 and 2 mark the two remaining classes (neither of them contains a 4-term AP):

..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222

That no such partition of [1,68] exists was confirmed by a second, independent encoding. The partition above is the previous term's with one more singleton, so the content of this term is the upper bound.
(End)
```

*Evidence behind the two sentences above, kept out of the comment because the editors asked for brevity: refutation 7269 s, all 40 cubes; witness 107 s; free construction alone would give only a(7) >= 68. The family gate reproduced the published a(6) = 67 before this term was claimed (validate_gate07.json).*

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222" 7 4 4
```

---

## NOT ready — do not submit these

* **A217059 a(9) = 74** — no family gate evidence reproducing the published a(8) = 70 — DO NOT SUBMIT. The Never list forbids claiming a term whose family gate did not reproduce the published value; run the gate and let it finish, then regenerate this pack
