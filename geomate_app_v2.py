import csv
import io
import json
import math
import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

try:
    from pyproj import CRS, Transformer
    HAS_PYPROJ = True
except Exception:
    CRS = None  # type: ignore
    Transformer = None  # type: ignore
    HAS_PYPROJ = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except Exception:
    openpyxl = None  # type: ignore
    HAS_OPENPYXL = False

try:
    import tkintermapview
    HAS_MAP = True
except Exception:
    tkintermapview = None  # type: ignore
    HAS_MAP = False

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    DND_FILES = None  # type: ignore
    TkinterDnD = None  # type: ignore
    HAS_DND = False

import main as core

LANG = {
    "ru": {"title": "GeoMate v2", "lang": "Язык", "theme": "Тема", "light": "Светлая", "dark": "Темная", "custom": "Свои параметры"},
    "en": {"title": "GeoMate v2", "lang": "Language", "theme": "Theme", "light": "Light", "dark": "Dark", "custom": "Custom parameters"},
}


def parse_row(line: str) -> List[float]:
    line = line.strip()
    if not line:
        return []
    line = line.replace(";", " ").replace(",", ".").replace("\t", " ")
    return [float(x) for x in line.split() if x]


class GeoMateV2:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = "ru"
        self.text = LANG[self.lang]
        self.root.title(self.text["title"])
        self.root.geometry("1300x850")
        self.style = ttk.Style(root)
        self.theme_var = tk.StringVar(value=self.text["light"])
        self._apply_theme()
        self.rf_db = self._load_rf_db()
        self.history_lines: List[str] = []
        self.custom_7params: Dict[str, str] = {"dX": "0", "dY": "0", "dZ": "0", "eX": "0", "eY": "0", "eZ": "0", "m": "0"}
        self._last_clip = ""

        top = ttk.Frame(root, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(top, text=self.text["lang"]).pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="RU")
        cb = ttk.Combobox(top, textvariable=self.lang_var, values=["RU", "EN"], width=7, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", self.change_lang)
        ttk.Label(top, text=self.text["theme"]).pack(side=tk.LEFT, padx=(12, 4))
        tcb = ttk.Combobox(top, textvariable=self.theme_var, values=[self.text["light"], self.text["dark"]], width=10, state="readonly")
        tcb.pack(side=tk.LEFT)
        tcb.bind("<<ComboboxSelected>>", lambda _: self._apply_theme())

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.tab_crs = ttk.Frame(self.nb, padding=10)
        self.tab_geo = ttk.Frame(self.nb, padding=10)
        self.tab_special = ttk.Frame(self.nb, padding=10)
        self.nb.add(self.tab_crs, text="CRS Transform")
        self.nb.add(self.tab_geo, text="Geodetic Core")
        self.nb.add(self.tab_special, text="Special workflow")

        self.build_crs_tab()
        self.build_geo_tab()
        self.build_special_tab()
        self.root.after(1200, self.autopaste_tick)

    def _load_rf_db(self) -> Dict[str, object]:
        p = os.path.join(os.path.dirname(__file__), "rf_crs_db.json")
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"default_wkt": "", "regions": []}

    def _apply_theme(self) -> None:
        dark = self.theme_var.get() in ("Dark", "Темная")
        self.style.theme_use("clam")
        if dark:
            bg = "#1e1e1e"; fg = "#f0f0f0"; field = "#2a2a2a"
        else:
            bg = "#f2f3f5"; fg = "#1f1f1f"; field = "#ffffff"
        self.root.configure(bg=bg)
        self.style.configure(".", background=bg, foreground=fg, fieldbackground=field)
        self.style.configure("TLabel", background=bg, foreground=fg)

    def change_lang(self, _event=None) -> None:
        self.lang = "en" if self.lang_var.get() == "EN" else "ru"
        self.text = LANG[self.lang]
        self.root.title(self.text["title"])

    def log(self, msg: str) -> None:
        s = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
        self.history_lines.append(s)
        self.history.insert("end", s + "\n")
        self.history.see("end")

    def build_crs_tab(self) -> None:
        f = ttk.Frame(self.tab_crs); f.pack(fill=tk.X)
        ttk.Label(f, text="Input CRS (EPSG/WKT):").grid(row=0, column=0, sticky="w")
        self.in_crs = ttk.Entry(f, width=40); self.in_crs.insert(0, "EPSG:4326"); self.in_crs.grid(row=0, column=1, padx=4)
        ttk.Label(f, text="Output CRS (EPSG/WKT):").grid(row=0, column=2, sticky="w")
        self.out_crs = ttk.Entry(f, width=40); self.out_crs.insert(0, "EPSG:3857"); self.out_crs.grid(row=0, column=3, padx=4)
        ttk.Label(f, text="Регион РФ").grid(row=1, column=0, sticky="w")
        self.region_var = tk.StringVar(value="")
        self.region_box = ttk.Combobox(f, textvariable=self.region_var, values=[r["name"] for r in self.rf_db.get("regions", [])], width=40, state="readonly")
        self.region_box.grid(row=1, column=1, padx=4, sticky="w")
        self.region_box.bind("<<ComboboxSelected>>", self.pick_region)
        ttk.Button(f, text=self.text["custom"], command=self.open_custom).grid(row=1, column=2, padx=4, sticky="w")

        sp = ttk.LabelFrame(self.tab_crs, text="Smart Paste")
        sp.pack(fill=tk.X, pady=6)
        ttk.Label(sp, text="X").grid(row=0, column=0); self.sp_x = ttk.Entry(sp, width=16); self.sp_x.grid(row=0, column=1, padx=4)
        ttk.Label(sp, text="Y").grid(row=0, column=2); self.sp_y = ttk.Entry(sp, width=16); self.sp_y.grid(row=0, column=3, padx=4)
        ttk.Button(sp, text="Auto-Parse Clipboard", command=self.smart_paste).grid(row=0, column=4, padx=4)
        self.sp_status = ttk.Label(sp, text="Ready"); self.sp_status.grid(row=0, column=5, padx=4)

        b = ttk.Frame(self.tab_crs); b.pack(fill=tk.X)
        ttk.Button(b, text="Import TXT", command=self.import_txt).pack(side=tk.LEFT, padx=2)
        ttk.Button(b, text="Import CSV/XLSX", command=self.import_table).pack(side=tk.LEFT, padx=2)
        ttk.Button(b, text="Transform", command=self.transform).pack(side=tk.LEFT, padx=2)
        ttk.Button(b, text="Export TXT", command=self.export_txt).pack(side=tk.LEFT, padx=2)

        pane = ttk.Panedwindow(self.tab_crs, orient=tk.HORIZONTAL); pane.pack(fill=tk.BOTH, expand=True, pady=6)
        l = ttk.Frame(pane); r = ttk.Frame(pane); pane.add(l, weight=1); pane.add(r, weight=1)
        ttk.Label(l, text="Input").pack(anchor="w"); self.input = tk.Text(l, height=14); self.input.pack(fill=tk.BOTH, expand=True)
        ttk.Label(r, text="Output").pack(anchor="w"); self.output = tk.Text(r, height=14); self.output.pack(fill=tk.BOTH, expand=True)

        mf = ttk.LabelFrame(self.tab_crs, text="Mini-Map Preview"); mf.pack(fill=tk.BOTH, expand=True)
        if HAS_MAP:
            self.mapw = tkintermapview.TkinterMapView(mf, width=500, height=240)  # type: ignore
            self.mapw.pack(fill=tk.BOTH, expand=True)
            self.mapw.set_position(55.75, 37.61); self.mapw.set_zoom(5)
            self.marker = self.mapw.set_marker(55.75, 37.61, text="GeoMate")
        else:
            self.mapw = None
            self.canvas = tk.Canvas(mf, height=240, bg="#12202d", highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.canvas.create_text(260, 30, text="Mini-map fallback", fill="#dbefff")
            self.dot = self.canvas.create_oval(255, 115, 265, 125, fill="#4ed0ff")

        dd = ttk.LabelFrame(self.tab_crs, text="Drag-and-Drop"); dd.pack(fill=tk.X, pady=4)
        self.drop = tk.Text(dd, height=3); self.drop.pack(fill=tk.X, padx=4, pady=4)
        self.drop.insert("1.0", "Drop .txt files here (if tkinterdnd2 is installed).")
        if HAS_DND:
            self.drop.drop_target_register(DND_FILES)  # type: ignore
            self.drop.dnd_bind("<<Drop>>", self.on_drop)  # type: ignore

    def build_geo_tab(self) -> None:
        f = ttk.Frame(self.tab_geo); f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="Vincenty inverse: B1 L1 B2 L2").grid(row=0, column=0, sticky="w")
        self.ib1 = ttk.Entry(f, width=12); self.ib1.grid(row=1, column=0, padx=2)
        self.il1 = ttk.Entry(f, width=12); self.il1.grid(row=1, column=1, padx=2)
        self.ib2 = ttk.Entry(f, width=12); self.ib2.grid(row=1, column=2, padx=2)
        self.il2 = ttk.Entry(f, width=12); self.il2.grid(row=1, column=3, padx=2)
        ttk.Button(f, text="Run inverse", command=self.run_inverse).grid(row=1, column=4, padx=4)
        ttk.Label(f, text="Vincenty forward: B1 L1 A12 S12").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.fb1 = ttk.Entry(f, width=12); self.fb1.grid(row=3, column=0, padx=2)
        self.fl1 = ttk.Entry(f, width=12); self.fl1.grid(row=3, column=1, padx=2)
        self.faz = ttk.Entry(f, width=12); self.faz.grid(row=3, column=2, padx=2)
        self.fs = ttk.Entry(f, width=12); self.fs.grid(row=3, column=3, padx=2)
        ttk.Button(f, text="Run forward", command=self.run_forward).grid(row=3, column=4, padx=4)
        ttk.Button(f, text="Ground-to-Grid", command=self.ground_to_grid).grid(row=4, column=0, sticky="w", pady=6)
        ttk.Button(f, text="МНК полярной засечки", command=self.run_mnk).grid(row=4, column=1, sticky="w", pady=6)
        self.geo_out = tk.Text(f, height=18); self.geo_out.grid(row=5, column=0, columnspan=5, sticky="nsew")
        ttk.Label(f, text="History").grid(row=6, column=0, sticky="w")
        self.history = tk.Text(f, height=8); self.history.grid(row=7, column=0, columnspan=5, sticky="nsew", pady=4)
        f.rowconfigure(5, weight=1); f.rowconfigure(7, weight=1)

    def build_special_tab(self) -> None:
        f = ttk.Frame(self.tab_special); f.pack(fill=tk.BOTH, expand=True)
        keys = ["b1", "l1", "h1", "b2", "l2", "h2"]
        self.spe: Dict[str, ttk.Entry] = {}
        for i, k in enumerate(keys):
            ttk.Label(f, text=k.upper()).grid(row=i // 3, column=(i % 3) * 2, sticky="w", padx=3, pady=3)
            e = ttk.Entry(f, width=14); e.grid(row=i // 3, column=(i % 3) * 2 + 1, padx=3, pady=3); self.spe[k] = e
        ttk.Button(f, text="Run items 1-9", command=self.run_special).grid(row=2, column=0, pady=6, sticky="w")
        self.spec_out = tk.Text(f, height=30); self.spec_out.grid(row=3, column=0, columnspan=6, sticky="nsew")
        f.rowconfigure(3, weight=1)

    def pick_region(self, _event=None) -> None:
        n = self.region_var.get()
        for r in self.rf_db.get("regions", []):
            if r.get("name") == n:
                self.in_crs.delete(0, tk.END)
                self.in_crs.insert(0, r.get("wkt", self.rf_db.get("default_wkt", "")))
                break

    def open_custom(self) -> None:
        w = tk.Toplevel(self.root); w.title(self.text["custom"]); w.geometry("760x500")
        ttk.Label(w, text="WKT / PRJ").pack(anchor="w", padx=6, pady=4)
        tw = tk.Text(w, height=10); tw.pack(fill=tk.X, padx=6)
        ttk.Label(w, text="7 params: dX dY dZ eX eY eZ m").pack(anchor="w", padx=6, pady=4)
        vars7 = [tk.StringVar(value="0") for _ in range(7)]
        rf = ttk.Frame(w); rf.pack(fill=tk.X, padx=6)
        for i, v in enumerate(vars7):
            ttk.Entry(rf, textvariable=v, width=10).grid(row=0, column=i, padx=2)

        def apply() -> None:
            wkt = tw.get("1.0", tk.END).strip()
            if wkt:
                self.in_crs.delete(0, tk.END); self.in_crs.insert(0, wkt)
            vals = [v.get().strip() for v in vars7]
            self.custom_7params = {"dX": vals[0], "dY": vals[1], "dZ": vals[2], "eX": vals[3], "eY": vals[4], "eZ": vals[5], "m": vals[6]}
            self.log(f"Custom 7-param updated: {self.custom_7params}")
            w.destroy()

        ttk.Button(w, text="Apply", command=apply).pack(anchor="e", padx=6, pady=8)

    def _clip_xy(self, text: str) -> Optional[Tuple[float, float]]:
        s = text.replace(",", ".")
        m = re.search(r"[Xx]\s*[:=]\s*(-?\d+(?:\.\d+)?)\D+[Yy]\s*[:=]\s*(-?\d+(?:\.\d+)?)", s)
        if m:
            return float(m.group(1)), float(m.group(2))
        nums = re.findall(r"-?\d+(?:\.\d+)?", s)
        if len(nums) >= 2:
            return float(nums[0]), float(nums[1])
        return None

    def smart_paste(self) -> None:
        try:
            t = self.root.clipboard_get()
        except Exception:
            return
        p = self._clip_xy(t)
        if not p:
            self.sp_status.configure(text="No XY")
            return
        x, y = p
        self.sp_x.delete(0, tk.END); self.sp_x.insert(0, f"{x}")
        self.sp_y.delete(0, tk.END); self.sp_y.insert(0, f"{y}")
        self.input.insert("end", f"{x} {y}\n")
        self.sp_status.configure(text=f"Parsed: {x:.4f}, {y:.4f}")
        self.update_map(x, y)

    def autopaste_tick(self) -> None:
        try:
            t = self.root.clipboard_get()
            if t and t != self._last_clip:
                self._last_clip = t
                p = self._clip_xy(t)
                if p:
                    x, y = p
                    self.sp_x.delete(0, tk.END); self.sp_x.insert(0, str(x))
                    self.sp_y.delete(0, tk.END); self.sp_y.insert(0, str(y))
                    self.update_map(x, y)
        except Exception:
            pass
        self.root.after(1200, self.autopaste_tick)

    def update_map(self, x: float, y: float) -> None:
        if self.mapw is not None:
            if -180 <= x <= 180 and -90 <= y <= 90:
                self.mapw.set_position(y, x)
                self.mapw.set_zoom(10)
                self.marker.delete()
                self.marker = self.mapw.set_marker(y, x, text=f"{y:.4f},{x:.4f}")
        else:
            xx = max(20, min(500, int(260 + x * 0.2)))
            yy = max(20, min(220, int(120 - y * 0.2)))
            self.canvas.coords(self.dot, xx - 6, yy - 6, xx + 6, yy + 6)

    def on_drop(self, event) -> None:
        data = str(event.data)
        paths = [p.strip("{}") for p in data.split()]
        for p in paths:
            if p.lower().endswith(".txt") and os.path.isfile(p):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    self.input.insert("end", f.read() + "\n")
        self.log("Drag-and-drop import done")

    def import_txt(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if not p:
            return
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            self.input.delete("1.0", tk.END)
            self.input.insert("1.0", f.read())

    def export_txt(self) -> None:
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.output.get("1.0", tk.END))

    def import_table(self) -> None:
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("XLSX", "*.xlsx"), ("All", "*.*")])
        if not p:
            return
        rows: List[str] = []
        if p.lower().endswith(".csv"):
            with open(p, "r", encoding="utf-8-sig", newline="") as f:
                for r in csv.reader(f):
                    if r:
                        rows.append(" ".join(str(x).strip() for x in r if str(x).strip()))
        elif p.lower().endswith(".xlsx"):
            if not HAS_OPENPYXL:
                raise RuntimeError("openpyxl missing")
            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            ws = wb.active
            for rr in ws.iter_rows(values_only=True):
                vals = [str(v).strip() for v in rr if v is not None and str(v).strip()]
                if vals:
                    rows.append(" ".join(vals))
        self.input.delete("1.0", tk.END)
        self.input.insert("1.0", "\n".join(rows))

    def transform(self) -> None:
        if not HAS_PYPROJ:
            messagebox.showerror("Transform", "Install pyproj")
            return
        try:
            tr = Transformer.from_crs(CRS.from_user_input(self.in_crs.get().strip() or "EPSG:4326"), CRS.from_user_input(self.out_crs.get().strip() or "EPSG:3857"), always_xy=True)
        except Exception as e:
            messagebox.showerror("CRS", str(e))
            return
        out = io.StringIO()
        wr = csv.writer(out, delimiter="\t", lineterminator="\n")
        for ln in self.input.get("1.0", tk.END).splitlines():
            if not ln.strip():
                continue
            try:
                v = parse_row(ln)
                if len(v) >= 3:
                    x, y, z = tr.transform(v[0], v[1], v[2])
                    wr.writerow([f"{x:.6f}", f"{y:.6f}", f"{z:.4f}"])
                elif len(v) >= 2:
                    x, y = tr.transform(v[0], v[1])
                    wr.writerow([f"{x:.6f}", f"{y:.6f}"])
                else:
                    wr.writerow([f"bad line: {ln}"])
            except Exception as e:
                wr.writerow([f"parse error: {ln} ({e})"])
        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", out.getvalue())
        self.log("CRS transform complete")

    def run_inverse(self) -> None:
        try:
            b1 = float(self.ib1.get().replace(",", ".")); l1 = float(self.il1.get().replace(",", "."))
            b2 = float(self.ib2.get().replace(",", ".")); l2 = float(self.il2.get().replace(",", "."))
            az, dist = core.vincenty_inverse(b1, l1, b2, l2)
            self.geo_out.delete("1.0", tk.END)
            self.geo_out.insert("1.0", f"A12={az:.10f} deg ({az*3600.0:.4f} arcsec)\nS12={dist:.4f} m\n")
            self.log("Vincenty inverse done")
        except Exception as e:
            messagebox.showerror("Inverse", str(e))

    def run_forward(self) -> None:
        try:
            b1 = float(self.fb1.get().replace(",", ".")); l1 = float(self.fl1.get().replace(",", "."))
            az = float(self.faz.get().replace(",", ".")); s = float(self.fs.get().replace(",", "."))
            b2, l2 = core.vincenty_forward(b1, l1, az, s)
            self.geo_out.delete("1.0", tk.END)
            self.geo_out.insert("1.0", f"B2={b2:.10f}\nL2={l2:.10f}\n")
            self.log("Vincenty forward done")
        except Exception as e:
            messagebox.showerror("Forward", str(e))

    def ground_to_grid(self) -> None:
        try:
            b = float(self.fb1.get().replace(",", ".")); l = float(self.fl1.get().replace(",", "."))
            s = float(self.fs.get().replace(",", "."))
            h = float(self.spe.get("h1").get().replace(",", ".")) if self.spe.get("h1") and self.spe.get("h1").get().strip() else 0.0
            r = 6378137.0
            s0 = s * (r / (r + h))
            k = 1.0
            if HAS_PYPROJ:
                try:
                    out_crs = CRS.from_user_input(self.out_crs.get().strip() or "EPSG:3857")
                    if out_crs.is_projected:
                        import pyproj
                        p = pyproj.Proj(out_crs.to_proj4())
                        fac = p.get_factors(l, b)
                        k = fac.meridional_scale
                except Exception:
                    k = 1.0
            sg = s0 * k
            self.geo_out.delete("1.0", tk.END)
            self.geo_out.insert("1.0", f"S_ground={s:.4f}\nH={h:.3f}\nS0=S*R/(R+H)={s0:.4f}\nk={k:.8f}\nS_grid={sg:.4f}\n")
            self.log("Ground-to-Grid done")
        except Exception as e:
            messagebox.showerror("Ground-to-Grid", str(e))

    def run_mnk(self) -> None:
        """
        Read lines from geo_out: x y d
        """
        try:
            obs: List[Tuple[float, float, float]] = []
            for ln in self.geo_out.get("1.0", tk.END).splitlines():
                v = parse_row(ln)
                if len(v) >= 3:
                    obs.append((v[0], v[1], v[2]))
            if len(obs) < 3:
                raise RuntimeError("Need >=3 lines: x y d")
            x = sum(o[0] for o in obs) / len(obs); y = sum(o[1] for o in obs) / len(obs)
            for _ in range(10):
                a11 = a12 = a22 = b1 = b2 = 0.0
                for xi, yi, di in obs:
                    r = math.hypot(x - xi, y - yi)
                    if r < 1e-12:
                        continue
                    ax = (x - xi) / r; ay = (y - yi) / r; li = di - r
                    a11 += ax * ax; a12 += ax * ay; a22 += ay * ay
                    b1 += ax * li; b2 += ay * li
                det = a11 * a22 - a12 * a12
                if abs(det) < 1e-15:
                    break
                dx = (b1 * a22 - b2 * a12) / det
                dy = (a11 * b2 - a12 * b1) / det
                x += dx; y += dy
                if math.hypot(dx, dy) < 1e-6:
                    break
            vtpv = 0.0
            for xi, yi, di in obs:
                r = math.hypot(x - xi, y - yi)
                v = di - r
                vtpv += v * v
            dof = max(1, len(obs) - 2)
            m0 = math.sqrt(vtpv / dof)
            det = a11 * a22 - a12 * a12
            q11 = a22 / det; q22 = a11 / det; q12 = -a12 / det
            tr = q11 + q22
            d = math.sqrt(max(0.0, (q11 - q22) * (q11 - q22) + 4.0 * q12 * q12))
            l1 = 0.5 * (tr + d); l2 = 0.5 * (tr - d)
            ae = m0 * math.sqrt(max(l1, 0.0)); be = m0 * math.sqrt(max(l2, 0.0))
            az = 0.5 * math.degrees(math.atan2(2.0 * q12, q11 - q22))
            self.geo_out.delete("1.0", tk.END)
            self.geo_out.insert("1.0", f"MNK result\nX={x:.4f}\nY={y:.4f}\nm0={m0:.4f}\nellipse a={ae:.4f} b={be:.4f} az={az:.4f}\n")
            self.log("MNK solved")
        except Exception as e:
            messagebox.showerror("MNK", str(e))

    def run_special(self) -> None:
        try:
            b1 = float(self.spe["b1"].get().replace(",", "."))
            l1 = float(self.spe["l1"].get().replace(",", "."))
            h1 = float(self.spe["h1"].get().replace(",", "."))
            b2 = float(self.spe["b2"].get().replace(",", "."))
            l2 = float(self.spe["l2"].get().replace(",", "."))
            h2 = float(self.spe["h2"].get().replace(",", "."))
            zone1 = core.get_zone_number(l1); zone2 = zone1 + 1
            x1, y1 = core.geodetic_to_gauss(b1, l1, zone1)
            b1c, l1c = core.gauss_to_geodetic(x1, y1, zone1)
            x1g, y1g = core.gost_zone_transform(x1, y1, zone1, zone2)
            az, s = core.vincenty_inverse(b1, l1, b2, l2)
            b2f, l2f = core.vincenty_forward(b1, l1, az, s)
            x2, y2 = core.geodetic_to_gauss(b2f, l2f, zone2)
            b95, l95, h95 = core.sk42_to_sk95(b2, l2, h2)
            rep = [
                f"zone1={zone1} zone2={zone2}",
                f"x1={x1:.3f} y1={y1:.3f}",
                f"control B1={b1c:.10f} L1={l1c:.10f}",
                f"adj zone x1'={x1g:.3f} y1'={y1g:.3f}",
                f"A12={az:.10f} S12={s:.4f}",
                f"x2={x2:.3f} y2={y2:.3f}",
                f"SK95 B2={b95:.10f} L2={l95:.10f} H2={h95:.3f}",
                f"H1={h1:.3f} H2={h2:.3f}",
            ]
            self.spec_out.delete("1.0", tk.END); self.spec_out.insert("1.0", "\n".join(rep))
            self.log("Special workflow done")
        except Exception as e:
            messagebox.showerror("Special", str(e))


def run() -> None:
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()  # type: ignore
    GeoMateV2(root)
    root.mainloop()


if __name__ == "__main__":
    run()
