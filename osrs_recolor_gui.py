#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSRS Recolor Indices → Java ARGB (int only) GUI
-----------------------------------------------
- Paste one or more NPC-like blocks containing recolorTo.
- Conversion uses the OSRS palette offsets: H = h/64 + 1/128, S = s/8 + 1/16, L = l/128.
- Optional pre-RGB lightness shading on the HSL index (l' = clamp(int(l*scale), min, max)).
- Optional brightness exponent (pow) post HSL→RGB (r=g=b=channel**exp).
- Outputs ONLY Java ARGB signed ints (0xFFRRGGBB) as a flat list.

Copy helper:
- Copy Java SearchablePixel array (all) with customizable array name, ColorModel, and threshold.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import scrolledtext
from typing import List, Tuple, Optional

# -------- Conversion logic --------

def unpack_hsl(packed: int) -> Tuple[int,int,int]:
    return (packed >> 10) & 0x3F, (packed >> 7) & 0x07, packed & 0x7F

def pack_hsl(h:int, s:int, l:int) -> int:
    return ((h & 0x3F) << 10) | ((s & 0x07) << 7) | (l & 0x7F)

def hsl_bits_to_floats_osrs_offsets(h:int, s:int, l:int) -> Tuple[float,float,float]:
    H = h / 64.0 + 1.0/128.0
    S = s / 8.0  + 1.0/16.0
    L = l / 128.0
    return H, S, L

def _hue2rgb(f: float, a: float, b: float) -> float:
    if f < 0.0: f += 1.0
    if f > 1.0: f -= 1.0
    if f < 1.0/6.0: return b + (a - b) * 6.0 * f
    if f < 1.0/2.0: return a
    if f < 2.0/3.0: return b + (a - b) * (2.0/3.0 - f) * 6.0
    return b

def hsl_to_rgb01(H: float, S: float, L: float) -> Tuple[float,float,float]:
    if S <= 0.0: return (L, L, L)
    if L < 0.5:
        a = L * (1.0 + S)
    else:
        a = (L + S) - (L * S)
    b = 2.0 * L - a
    r = _hue2rgb(H + 1.0/3.0, a, b)
    g = _hue2rgb(H, a, b)
    bl= _hue2rgb(H - 1.0/3.0, a, b)
    return (r, g, bl)

def apply_brightness_exponent(rgb01: Tuple[float,float,float], exponent: Optional[float]) -> Tuple[float,float,float]:
    if exponent is None or abs(exponent - 1.0) < 1e-12:
        return rgb01
    r, g, b = rgb01
    r = r ** exponent
    g = g ** exponent
    b = b ** exponent
    r = 0.0 if r < 0.0 else (1.0 if r > 1.0 else r)
    g = 0.0 if g < 0.0 else (1.0 if g > 1.0 else g)
    b = 0.0 if b < 0.0 else (1.0 if b > 1.0 else b)
    return (r, g, b)

def rgb01_to_rgb8(rgb01: Tuple[float,float,float]) -> Tuple[int,int,int]:
    r, g, b = rgb01
    ri = int(r * 256.0); gi = int(g * 256.0); bi = int(b * 256.0)
    ri = 0 if ri < 0 else (255 if ri > 255 else ri)
    gi = 0 if gi < 0 else (255 if gi > 255 else gi)
    bi = 0 if bi < 0 else (255 if bi > 255 else bi)
    return ri, gi, bi

def rgb_to_argb_int(r:int, g:int, b:int) -> int:
    argb = (0xFF << 24) | (r << 16) | (g << 8) | b
    return argb - (1 << 32) if argb >= (1 << 31) else argb

def argb_hex(argb_signed:int) -> str:
    return f"0x{(argb_signed & 0xFFFFFFFF):08X}"

def shade_lightness_on_index(packed:int, scale:float, lmin:int=2, lmax:int=126) -> int:
    if scale is None or abs(scale - 1.0) < 1e-9: 
        return packed
    h, s, l = unpack_hsl(packed)
    newL = int(l * float(scale))
    if newL < lmin: newL = lmin
    if newL > lmax: newL = lmax
    if newL < 0: newL = 0
    if newL > 127: newL = 127
    return pack_hsl(h, s, newL)

# -------- Parsing helpers --------

def split_curly_blocks(text: str) -> List[str]:
    blocks, depth, start = [], 0, None
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    blocks.append(text[start:i+1]); start = None
    return blocks

import re as _re
COUNT_BLOCK_RE = _re.compile(r"\(\s*\d+\s*\)\s*\[", _re.MULTILINE)

def extract_ints_from_bracket_block(block_text: str) -> List[int]:
    cleaned = COUNT_BLOCK_RE.sub("[", block_text)
    nums = _re.findall(r"-?\d+", cleaned)
    vals = []
    for tok in nums:
        try:
            v = int(tok, 10)
            if 0 <= v <= 65535: vals.append(v)
        except Exception:
            pass
    return vals

def find_array_after(label: str, text: str) -> Optional[List[int]]:
    m = _re.search(rf"{_re.escape(label)}\s*:\s*\(\s*\d+\s*\)\s*\[(.*?)\]", text, _re.DOTALL | _re.IGNORECASE)
    if not m:
        m = _re.search(rf"{_re.escape(label)}\s*:\s*\[(.*?)\]", text, _re.DOTALL | _re.IGNORECASE)
        if not m: return None
    return extract_ints_from_bracket_block(m.group(1))

def find_id(text: str) -> Optional[int]:
    m = _re.search(r"\bid\s*:\s*(-?\d+)", text, _re.IGNORECASE)
    if m:
        try: return int(m.group(1))
        except Exception: return None
    return None

def find_name(text: str) -> Optional[str]:
    m = _re.search(r'\bname\s*:\s*"([^"]*)"', text, _re.IGNORECASE)
    return m.group(1) if m else None

# -------- GUI --------

class RecolorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Recolor → Java ARGB (int only)")
        self.geometry("980x700")
        self.minsize(860, 620)
        self._run_after_id = None
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=8); top.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1); self.columnconfigure(0, weight=1)

        ttk.Label(top, text="Paste one or more blocks (or a list) containing recolorTo:").grid(row=0, column=0, columnspan=10, sticky="w")
        self.txt_input = scrolledtext.ScrolledText(top, height=14, wrap="word")
        self.txt_input.grid(row=1, column=0, columnspan=10, sticky="nsew", pady=(4, 8))
        top.rowconfigure(1, weight=1)
        for c in range(10): top.columnconfigure(c, weight=1 if c==9 else 0)

        controls = ttk.Frame(top); controls.grid(row=2, column=0, columnspan=10, sticky="ew", pady=(0,6))
        for c in range(20): controls.columnconfigure(c, weight=0)
        controls.columnconfigure(19, weight=1)

        ttk.Label(controls, text="Brightness exp (pow):").grid(row=0, column=0, sticky="w")
        self.exp_var = tk.StringVar()
        self.exp_var.trace_add("write", self._on_entry_change)
        self.ent_exp = ttk.Entry(controls, width=10, textvariable=self.exp_var)
        self.ent_exp.grid(row=0, column=1, sticky="w", padx=(4,16))

        ttk.Label(controls, text="Lightness L× (pre-RGB):").grid(row=0, column=2, sticky="w")
        self.lscale_var = tk.StringVar()
        self.lscale_var.trace_add("write", self._on_entry_change)
        self.ent_lscale = ttk.Entry(controls, width=8, textvariable=self.lscale_var)
        self.ent_lscale.grid(row=0, column=3, sticky="w", padx=(4,8))

        ttk.Label(controls, text="Clamp L[min,max]:").grid(row=0, column=4, sticky="w")
        self.lmin_var = tk.StringVar(value="2")
        self.lmax_var = tk.StringVar(value="126")
        self.lmin_var.trace_add("write", self._on_entry_change)
        self.lmax_var.trace_add("write", self._on_entry_change)
        self.ent_lmin = ttk.Entry(controls, width=5, textvariable=self.lmin_var)
        self.ent_lmin.grid(row=0, column=5, sticky="w", padx=(4,2))
        self.ent_lmax = ttk.Entry(controls, width=5, textvariable=self.lmax_var)
        self.ent_lmax.grid(row=0, column=6, sticky="w", padx=(2,12))

        ttk.Label(controls, text="Output:").grid(row=0, column=7, sticky="w")
        self.apply_var = tk.StringVar(value="To (shaded)")
        self.cmb_apply = ttk.Combobox(
            controls,
            state="readonly",
            width=12,
            values=["To (shaded)", "To (no shade)"],
            textvariable=self.apply_var,
        )
        self.cmb_apply.current(0)
        self.cmb_apply.grid(row=0, column=8, sticky="w", padx=(4,16))
        self.cmb_apply.bind("<<ComboboxSelected>>", self._on_control_change)

        # Java array generation controls
        arrbar = ttk.Frame(top); arrbar.grid(row=3, column=0, columnspan=10, sticky="ew", pady=(0,6))
        for c in range(20): arrbar.columnconfigure(c, weight=0)
        arrbar.columnconfigure(19, weight=1)

        ttk.Label(arrbar, text="Array name:").grid(row=0, column=0, sticky="w")
        self.ent_arrname = ttk.Entry(arrbar, width=30); self.ent_arrname.insert(0, "SearchableArray"); self.ent_arrname.grid(row=0, column=1, sticky="w", padx=(4,12))

        ttk.Label(arrbar, text="ColorModel:").grid(row=0, column=2, sticky="w")
        self.cmb_colormodel = ttk.Combobox(arrbar, state="readonly", width=8, values=["HSL","RGB"])
        self.cmb_colormodel.current(0); self.cmb_colormodel.grid(row=0, column=3, sticky="w", padx=(4,12))

        ttk.Label(arrbar, text="Threshold:").grid(row=0, column=4, sticky="w")
        self.ent_thresh = ttk.Entry(arrbar, width=6); self.ent_thresh.insert(0, "2"); self.ent_thresh.grid(row=0, column=5, sticky="w", padx=(4,16))

        # Output tab: ARGB only
        bottom = ttk.Frame(self, padding=(8,0,8,8)); bottom.grid(row=1, column=0, sticky="nsew"); self.rowconfigure(1, weight=1)
        self.nb = ttk.Notebook(bottom); self.nb.pack(fill="both", expand=True)

        self.tab_argb = ttk.Frame(self.nb); self.nb.add(self.tab_argb, text="ARGB Output")
        tbar = ttk.Frame(self.tab_argb); tbar.pack(fill="x", padx=4, pady=4)

        ttk.Button(tbar, text="Copy Java array (all)", command=self.copy_java_array_all).pack(side="left")

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(tbar, textvariable=self.status_var).pack(side="right")

        self.tree = ttk.Treeview(self.tab_argb, columns=("argb",), show="headings", height=16, selectmode="extended")
        self.tree.heading("argb", text="ARGB (Java int)")
        self.tree.column("argb", width=200, anchor="e")

        vsb = ttk.Scrollbar(self.tab_argb, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4,0), pady=(0,8))
        vsb.pack(side="left", fill="y", pady=(0,8))

        # Example
        example = (
            "(12){\n"
            "id: 11904\n"
            "name: \"Guard\"\n"
            "recolorFrom: (5)[\n43072\n926\n5648\n61\n11200\n]\n"
            "recolorTo: (5)[\n8115\n8115\n8596\n10320\n8115\n]\n"
            "}\n"
        )
        self.txt_input.insert("1.0", example)
        self.txt_input.edit_modified(False)
        self.txt_input.bind("<<Modified>>", self._on_text_modified)

        self.schedule_conversion()

    # ---- Actions ----

    def _read_controls(self):
        exp_txt = self.exp_var.get().strip()
        exponent = None
        if exp_txt:
            try:
                exponent = float(exp_txt)
                if exponent <= 0.0:
                    raise ValueError
            except Exception as exc:
                raise ValueError("Brightness exponent must be a positive number (e.g., 0.8, 1.2).") from exc
        lscale_txt = self.lscale_var.get().strip()
        lscale = 1.0
        if lscale_txt:
            try:
                lscale = float(lscale_txt)
                if lscale < 0.0:
                    raise ValueError
            except Exception as exc:
                raise ValueError("Lightness scale must be a non-negative number (e.g., 1.0, 0.75, 1.2).") from exc
        try:
            lmin = int(self.lmin_var.get().strip() or "2")
            lmax = int(self.lmax_var.get().strip() or "126")
            if not (0 <= lmin <= 127 and 0 <= lmax <= 127 and lmin <= lmax):
                raise ValueError
        except Exception as exc:
            raise ValueError("Clamp values must be integers within 0..127 and min ≤ max (default 2..126).") from exc
        apply_to = self.apply_var.get()
        return exponent, lscale, lmin, lmax, apply_to

    def _index_to_rgb(self, packed:int, exponent:Optional[float]):
        h, s, l = unpack_hsl(packed)
        H, S, L = hsl_bits_to_floats_osrs_offsets(h, s, l)
        rgb01 = hsl_to_rgb01(H, S, L)
        rgb01 = apply_brightness_exponent(rgb01, exponent)
        return rgb01_to_rgb8(rgb01)

    def run_conversion(self):
        if self._run_after_id is not None:
            self.after_cancel(self._run_after_id)
            self._run_after_id = None
        try:
            args = self._read_controls()
        except ValueError as exc:
            self.status_var.set(f"Invalid input: {exc}")
            return
        exponent, lscale, lmin, lmax, apply_setting = args

        text = self.txt_input.get("1.0", "end")
        blocks = split_curly_blocks(text)

        self.tree.delete(*self.tree.get_children())
        count_blocks = 0
        count_vals = 0

        # Parse the apply_setting to determine what to output
        use_shading = "shaded" in apply_setting.lower()

        for b in blocks:
            arr_to = find_array_after("recolorTo", b) or []

            # Process each index
            for idx in arr_to:
                shaded = idx
                if use_shading:
                    shaded = shade_lightness_on_index(idx, lscale, lmin, lmax)
                r, g, b = self._index_to_rgb(shaded, exponent)
                argb = rgb_to_argb_int(r, g, b)
                self.tree.insert("", "end", values=(argb,))
                count_vals += 1

            count_blocks += 1

        self.status_var.set(
            f"Parsed {count_blocks} block(s). Output {count_vals} ARGB values ({apply_setting}). exp={exponent if exponent is not None else 1.0}"
        )

    def schedule_conversion(self, *_):
        if self._run_after_id is not None:
            self.after_cancel(self._run_after_id)
        self._run_after_id = self.after(400, self.run_conversion)

    def _on_text_modified(self, _event):
        if self.txt_input.edit_modified():
            self.schedule_conversion()
            self.txt_input.edit_modified(False)

    def _on_control_change(self, _event):
        self.schedule_conversion()

    def _on_entry_change(self, *_):
        self.schedule_conversion()

    # ---- Copy helpers ----

    def _collect_argb(self) -> List[int]:
        items = self.tree.get_children()
        vals = []
        for iid in items:
            try:
                v = int(self.tree.item(iid, "values")[0])
                vals.append(v)
            except Exception:
                pass
        return vals

    def copy_java_array_all(self):
        vals = self._collect_argb()
        if not vals:
            messagebox.showinfo("Copy", "No ARGB values to copy.")
            return
        name = self.ent_arrname.get().strip()
        if not name or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            messagebox.showerror("Array name", "Please provide a valid Java identifier for the array name (e.g., GUARD_HIGHLIGHT).")
            return
        model = self.cmb_colormodel.get().strip()
        try:
            thr = int(self.ent_thresh.get().strip())
        except Exception:
            messagebox.showerror("Threshold", "Threshold must be an integer (e.g., 2).")
            return

        # Build formatted Java code
        # Align columns nicely: int column width depends on max length of decimal strings
        decs = [str(v) for v in vals]
        w = max(len(s) for s in decs) if decs else 1
        lines = []
        lines.append(f"private static final SearchablePixel[] {name} = new SearchablePixel[]{{")
        for i, s in enumerate(decs):
            pad = " " * (w - len(s))
            comma = "," if i < len(decs) - 1 else ""
            lines.append(f"      new SearchablePixel({s}{pad}, new SingleThresholdComparator({thr}), ColorModel.{model}){comma}")
        lines.append("};")
        data = "\n".join(lines)

        self.clipboard_clear(); self.clipboard_append(data); self.update()
        messagebox.showinfo("Copy", f"Copied Java array with {len(vals)} entries to clipboard.")

def main():
    app = RecolorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
