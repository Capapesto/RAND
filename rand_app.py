"""
RAND Controller — Desktop App
Abas: Gesture Manager | Finger Simulator
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import serial
import serial.tools.list_ports
import threading
import json
import math
import time
from dataclasses import dataclass, field
from typing import Optional

# ════════════════════════════════════════════════
#  PALETA di gor
# ════════════════════════════════════════════════
C = {
    "bg":         "#4A5740",   # verde musgo escuro (janela)
    "panel":      "#5C6B54",   # painéis de dentro
    "panel_dark": "#3A4532",   # painéis mais fundos
    "titlebar":   "#2E3D28",   # barra do título
    "accent":     "#8BAF6E",   # verde claro dos botões ativos
    "accent2":    "#A8C98A",   
    "btn":        "#6B7D5E",   # botão normal
    "btn_press":  "#4A5A40",   # botão pressionado
    "text":       "#E8F0E0",   # texto principal
    "text_dim":   "#A0B090",   # texto secundário
    "border":     "#2A3525",   # bordas
    "border_hi":  "#9AB87A",   # borda destacada
    "red":        "#C05050",   # erro / delete
    "red_hi":     "#E07070",
    "yellow":     "#C0A040",   # aviso / gravando
    "green_hi":   "#70C070",   # conectado
    "entry_bg":   "#3A4532",
    "log_bg":     "#252E20",
    "log_ok":     "#80C870",
    "log_err":    "#E07070",
    "log_warn":   "#C8A040",
    "log_info":   "#80A8C8",
}

FONT_TITLE  = ("Tahoma", 11, "bold")
FONT_BODY   = ("Tahoma",  9)
FONT_SMALL  = ("Tahoma",  8)
FONT_MONO   = ("Courier New", 9)
FONT_BIG    = ("Tahoma", 14, "bold")


# ════════════════════════════════════════════════
#  CONEXÃO SERIAL
# ════════════════════════════════════════════════
class SerialManager:
    def __init__(self, on_line, on_state):
        self.on_line  = on_line   # callback(str)
        self.on_state = on_state  # callback(bool connected)
        self.ser: Optional[serial.Serial] = None
        self._running = False

    def list_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port, baud=115200):
        try:
            self.ser = serial.Serial(port, baud, timeout=0.1)
            self._running = True
            threading.Thread(target=self._read_loop, daemon=True).start()
            self.on_state(True)
            self.send("RAND_HELLO")
        except Exception as e:
            self.on_state(False)
            raise e

    def disconnect(self):
        self._running = False
        if self.ser and self.ser.is_open:
            try:
                self.send("RAND_BYE")
                time.sleep(0.1)
                self.ser.close()
            except: pass
        self.on_state(False)

    def send(self, cmd: str):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())

    def _read_loop(self):
        buf = ""
        while self._running:
            try:
                if self.ser and self.ser.in_waiting:
                    buf += self.ser.read(self.ser.in_waiting).decode(errors="replace")
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if line:
                            self.on_line(line)
                else:
                    time.sleep(0.02)
            except Exception:
                self._running = False
                self.on_state(False)
                break


# ════════════════════════════════════════════════
#  WIDGETS
# ════════════════════════════════════════════════
def xp_btn(parent, text, cmd=None, color=None, width=12, **kw):
    bg = color or C["btn"]
    b = tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg=C["text"], relief="raised",
        bd=2, font=FONT_BODY, width=width,
        activebackground=C["accent2"], activeforeground=C["text"],
        cursor="hand2", **kw
    )
    return b

def xp_label(parent, text, big=False, dim=False, **kw):
    fg = C["text_dim"] if dim else C["text"]
    f  = FONT_TITLE if big else FONT_BODY
    return tk.Label(parent, text=text, bg=C["panel"], fg=fg, font=f, **kw)

def xp_entry(parent, width=20, **kw):
    e = tk.Entry(
        parent, width=width,
        bg=C["entry_bg"], fg=C["text"],
        insertbackground=C["accent"],
        relief="sunken", bd=2, font=FONT_BODY, **kw
    )
    return e

def sep(parent):
    return tk.Frame(parent, bg=C["border"], height=2)


# ════════════════════════════════════════════════
#  ABA 1 — GESTURE MANAGER
# ════════════════════════════════════════════════
class GestureManagerTab(tk.Frame):
    def __init__(self, parent, serial_mgr: SerialManager):
        super().__init__(parent, bg=C["panel"])
        self.sm = serial_mgr
        self.gestures = []
        self._build()

    def _build(self):
        # lista de gestos 
        left = tk.Frame(self, bg=C["panel"], width=260)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        left.pack_propagate(False)

        xp_label(left, "GESTOS SALVOS", big=True).pack(anchor="w", pady=(0,6))

        # lista com scrollbar
        lb_frame = tk.Frame(left, bg=C["border"], bd=1, relief="sunken")
        lb_frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(lb_frame, bg=C["panel_dark"])
        self.listbox = tk.Listbox(
            lb_frame, yscrollcommand=scroll.set,
            bg=C["log_bg"], fg=C["text"],
            selectbackground=C["accent"], selectforeground=C["text"],
            font=FONT_MONO, bd=0, highlightthickness=0,
            activestyle="none"
        )
        scroll.config(command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Botões de ação da lista
        btn_row = tk.Frame(left, bg=C["panel"])
        btn_row.pack(fill="x", pady=(6,0))
        xp_btn(btn_row, "↻ Atualizar", self._refresh, width=12).pack(side="left")
        xp_btn(btn_row, "✕ Deletar", self._delete_selected, C["red"], width=10).pack(side="right")

        btn_row2 = tk.Frame(left, bg=C["panel"])
        btn_row2.pack(fill="x", pady=(4,0))
        xp_btn(btn_row2, "✔ Habilitar", self._enable, C["accent"], width=12).pack(side="left")
        xp_btn(btn_row2, "✖ Desabilitar", self._disable, width=11).pack(side="right")

        sep(left).pack(fill="x", pady=8)

        # Factory reset
        xp_btn(left, "⚠ Factory Reset", self._factory_reset,
               C["red"], width=22).pack(fill="x")

        #  Coluna direita: criar gesto + log 
        right = tk.Frame(self, bg=C["panel"])
        right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)

        # Criar gesto
        card = tk.LabelFrame(
            right, text=" NOVO GESTO ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove",
            labelanchor="nw"
        )
        card.pack(fill="x", pady=(0,8))

        r1 = tk.Frame(card, bg=C["panel"])
        r1.pack(fill="x", padx=8, pady=(6,4))
        xp_label(r1, "Nome:").pack(side="left")
        self.name_entry = xp_entry(r1, width=18)
        self.name_entry.pack(side="left", padx=(6,16))

        xp_label(r1, "Tipo:").pack(side="left")
        self.type_var = tk.StringVar(value="Estático")
        type_box = ttk.Combobox(
            r1, textvariable=self.type_var,
            values=["Estático", "Dinâmico"], width=10,
            state="readonly", font=FONT_BODY
        )
        type_box.pack(side="left", padx=(6,0))

        r2 = tk.Frame(card, bg=C["panel"])
        r2.pack(fill="x", padx=8, pady=(0,4))
        xp_label(r2, "Saída:").pack(side="left")
        self.out_var = tk.StringVar(value="Comando BLE")
        out_box = ttk.Combobox(
            r2, textvariable=self.out_var,
            values=["Comando BLE", "Mouse HID", "Tecla HID"], width=12,
            state="readonly", font=FONT_BODY
        )
        out_box.pack(side="left", padx=(6,16))
        xp_label(r2, "Valor:").pack(side="left")
        self.out_val = xp_entry(r2, width=16)
        self.out_val.insert(0, "meu_comando")
        self.out_val.pack(side="left", padx=(6,0))

        btn_row3 = tk.Frame(card, bg=C["panel"])
        btn_row3.pack(fill="x", padx=8, pady=(4,8))

        self.rec_btn = xp_btn(btn_row3, "⏺ Gravar", self._start_record,
                               C["accent"], width=14)
        self.rec_btn.pack(side="left")

        self.stop_btn = xp_btn(btn_row3, "⏹ Finalizar", self._stop_record,
                                C["yellow"], width=14)
        self.stop_btn.pack(side="left", padx=(8,0))
        self.stop_btn.config(state="disabled")

        xp_btn(btn_row3, "✕ Cancelar", self._cancel_record,
               width=12).pack(side="right")

        # Status de gravação
        self.rec_status = tk.Label(
            card, text="● Pronto", bg=C["panel"],
            fg=C["text_dim"], font=FONT_SMALL
        )
        self.rec_status.pack(anchor="w", padx=8, pady=(0,4))

        # Calibração flex
        cal_card = tk.LabelFrame(
            right, text=" CALIBRAÇÃO FLEX ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove", labelanchor="nw"
        )
        cal_card.pack(fill="x", pady=(0,8))

        cal_row = tk.Frame(cal_card, bg=C["panel"])
        cal_row.pack(fill="x", padx=8, pady=6)

        for label, default, cmd_fn in [
            ("Threshold", "0.50", self._set_threshold),
            ("R_div (Ω)", "33000", self._set_rdiv),
        ]:
            tk.Label(cal_row, text=label+":", bg=C["panel"],
                     fg=C["text"], font=FONT_SMALL).pack(side="left")
            e = xp_entry(cal_row, width=8)
            e.insert(0, default)
            e.pack(side="left", padx=(4,8))
            setattr(self, f"_e_{label.split()[0].lower()}", e)

        xp_btn(cal_row, "Aplicar", self._apply_calibration,
               width=10).pack(side="left")
        xp_btn(cal_row, "GET", self._get_sensors,
               width=6).pack(side="left", padx=(6,0))

        # Log
        log_frame = tk.LabelFrame(
            right, text=" LOG SERIAL ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove", labelanchor="nw"
        )
        log_frame.pack(fill="both", expand=True)

        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side="right", fill="y")
        self.log = tk.Text(
            log_frame, bg=C["log_bg"], fg=C["text"],
            font=FONT_MONO, bd=0, state="disabled",
            yscrollcommand=log_scroll.set,
            height=8, wrap="word"
        )
        self.log.pack(fill="both", expand=True, padx=2, pady=2)
        log_scroll.config(command=self.log.yview)

        self.log.tag_config("ok",   foreground=C["log_ok"])
        self.log.tag_config("err",  foreground=C["log_err"])
        self.log.tag_config("warn", foreground=C["log_warn"])
        self.log.tag_config("info", foreground=C["log_info"])

        btn_log = tk.Frame(right, bg=C["panel"])
        btn_log.pack(fill="x", pady=(4,0))
        xp_btn(btn_log, "Limpar log", self._clear_log, width=12).pack(side="right")

        self._is_recording = False
        self._rec_type = "static"

    #  Ações
    def _refresh(self):
        self.sm.send("LIST")
        self.log_msg("→ LIST enviado", "info")

    def _on_select(self, e):
        pass

    def _selected_id(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("RAND", "Selecione um gesto.")
            return None
        item = self.listbox.get(sel[0])
        return int(item.split("]")[0].replace("[","").strip())

    def _delete_selected(self):
        gid = self._selected_id()
        if gid is None: return
        if messagebox.askyesno("Deletar", f"Deletar gesto ID {gid}?"):
            self.sm.send(f"DEL:{gid}")
            self.log_msg(f"→ DEL:{gid}", "warn")

    def _enable(self):
        gid = self._selected_id()
        if gid is not None:
            self.sm.send(f"ENABLE:{gid}")
            self.log_msg(f"→ ENABLE:{gid}", "ok")

    def _disable(self):
        gid = self._selected_id()
        if gid is not None:
            self.sm.send(f"DISABLE:{gid}")
            self.log_msg(f"→ DISABLE:{gid}", "warn")

    def _factory_reset(self):
        if messagebox.askyesno("⚠ Factory Reset",
                                "Apagar TODOS os gestos? Irreversível."):
            self.sm.send("FACTORY_RESET")
            self.log_msg("→ FACTORY_RESET", "err")
            self.listbox.delete(0, "end")

    def _start_record(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("RAND", "Digite um nome para o gesto.")
            return
        tipo = self.type_var.get()
        if tipo == "Estático":
            self.sm.send(f"REC_STATIC:{name}")
            self._is_recording = True
            self._rec_type = "static"
            self.rec_status.config(text="⏺ Gravando estático...", fg=C["yellow"])
            self.rec_btn.config(state="disabled")
            self.log_msg(f"→ REC_STATIC:{name}", "warn")
        else:
            self.sm.send(f"REC_DYN_START:{name}")
            self._is_recording = True
            self._rec_type = "dynamic"
            self.rec_status.config(text="⏺ Gravando dinâmico...", fg=C["yellow"])
            self.rec_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.log_msg(f"→ REC_DYN_START:{name}", "warn")

    def _stop_record(self):
        if self._rec_type == "dynamic":
            self.sm.send("REC_DYN_END")
            self.log_msg("→ REC_DYN_END", "ok")
        self._reset_rec_ui()

    def _cancel_record(self):
        self.sm.send("REC_CANCEL")
        self.log_msg("→ REC_CANCEL", "warn")
        self._reset_rec_ui()

    def _reset_rec_ui(self):
        self._is_recording = False
        self.rec_status.config(text="● Pronto", fg=C["text_dim"])
        self.rec_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _set_threshold(self): pass
    def _set_rdiv(self): pass

    def _apply_calibration(self):
        thr  = self._e_threshold.get().strip()
        rdiv = self._e_r_div.get().strip()
        self.sm.send(f"FLEX_THR:{thr}")
        self.sm.send(f"FLEX_RDIV:{rdiv}")
        self.log_msg(f"→ FLEX_THR:{thr}  FLEX_RDIV:{rdiv}", "info")

    def _get_sensors(self):
        self.sm.send("GET_SENSORS")
        self.log_msg("→ GET_SENSORS", "info")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def log_msg(self, msg: str, tag="ok"):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", f"[{ts}] {msg}\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def on_serial_line(self, line: str):
        """Chamado pela thread serial com dados recebidos do ESP32."""
        # Classifica o tipo de mensagem
        if line.startswith("LIST:"):
            self._parse_list(line[5:])
        elif line.startswith("OK"):
            self.log_msg(f"← {line}", "ok")
            if "REC" in line:
                self._reset_rec_ui()
                self.after(300, self._refresh)
        elif line.startswith("ERR"):
            self.log_msg(f"← {line}", "err")
        elif line.startswith("SENSORS:"):
            self._show_sensors(line[8:])
        elif line.startswith("STATE:"):
            self.log_msg(f"← {line}", "info")
        elif line.startswith("BLE:"):
            tag = "ok" if "CONNECTED" in line else "warn"
            self.log_msg(f"← {line}", tag)
        else:
            self.log_msg(f"← {line}")

    def _parse_list(self, raw: str):
        try:
            items = json.loads(raw)
            self.listbox.delete(0, "end")
            self.gestures = items
            for g in items:
                tipo = "S" if g.get("type")==0 else "D"
                enab = "✔" if g.get("enabled") else "✖"
                self.listbox.insert(
                    "end",
                    f"[{g['id']:02d}] {enab} ({tipo}) {g['name']}"
                )
            self.log_msg(f"← {len(items)} gesto(s) recebido(s).", "ok")
        except Exception as e:
            self.log_msg(f"← Erro ao parsear LIST: {e}", "err")

    def _show_sensors(self, raw: str):
        try:
            d = json.loads(raw)
            msg = (f"pitch={d['pitch']:.1f}° roll={d['roll']:.1f}°  "
                   f"gx={d['gx']:.1f} gy={d['gy']:.1f}  "
                   f"flex=[{d['flex0']:.2f},{d['flex1']:.2f}]  "
                   f"back={d['btn_back']} fwd={d['btn_fwd']}")
            self.log_msg(f"SENSORS: {msg}", "info")
        except:
            self.log_msg(f"← {raw}", "info")


# ════════════════════════════════════════════════
#  ABA 2 (dedo fake
# ════════════════════════════════════════════════
class FingerSimulatorTab(tk.Frame):
    def __init__(self, parent, serial_mgr: SerialManager):
        super().__init__(parent, bg=C["panel"])
        self.sm = serial_mgr

        # Estado dos sensores simulados
        self.flex_vals  = [tk.DoubleVar(value=0.0),
                           tk.DoubleVar(value=0.0)]
        self.pitch_var  = tk.DoubleVar(value=0.0)
        self.roll_var   = tk.DoubleVar(value=0.0)
        self.btn_back   = tk.BooleanVar(value=False)
        self.btn_fwd    = tk.BooleanVar(value=False)
        self.btn_scroll = tk.BooleanVar(value=False)

        self._build()

    def _build(self):
        # Linha superior: mao+ mpu
        top = tk.Frame(self, bg=C["panel"])
        top.pack(fill="x", padx=8, pady=8)

        # mão
        hand_card = tk.LabelFrame(
            top, text=" VISUALIZAÇÃO DA MÃO ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove"
        )
        hand_card.pack(side="left", padx=(0,8))

        self.canvas = tk.Canvas(
            hand_card, width=260, height=280,
            bg=C["panel_dark"], bd=0, highlightthickness=0
        )
        self.canvas.pack(padx=6, pady=6)

        # MPU
        mpu_card = tk.LabelFrame(
            top, text=" MPU6050 (SIMULADO) ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove"
        )
        mpu_card.pack(side="left", fill="both", expand=True)

        for label, var, mn, mx in [
            ("Pitch (°)", self.pitch_var, -90, 90),
            ("Roll  (°)", self.roll_var,  -90, 90),
        ]:
            row = tk.Frame(mpu_card, bg=C["panel"])
            row.pack(fill="x", padx=10, pady=6)
            tk.Label(row, text=label, width=10, anchor="w",
                     bg=C["panel"], fg=C["text"], font=FONT_BODY).pack(side="left")
            sl = tk.Scale(
                row, variable=var, from_=mn, to=mx,
                orient="horizontal", length=180,
                bg=C["panel"], fg=C["text"],
                troughcolor=C["panel_dark"],
                highlightthickness=0, bd=0,
                sliderlength=18, command=lambda *_: self._redraw()
            )
            sl.pack(side="left")
            tk.Label(row, textvariable=var, width=5,
                     bg=C["panel"], fg=C["accent"], font=FONT_MONO).pack(side="left", padx=(4,0))

        # mini MPU ( bola)
        self.mpu_canvas = tk.Canvas(
            mpu_card, width=140, height=140,
            bg=C["panel_dark"], bd=0, highlightthickness=0
        )
        self.mpu_canvas.pack(pady=(0,8))

        #  Flex sliders
        flex_card = tk.LabelFrame(
            self, text=" FLEX SENSORS ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove"
        )
        flex_card.pack(fill="x", padx=8, pady=(0,8))

        flex_inner = tk.Frame(flex_card, bg=C["panel"])
        flex_inner.pack(fill="x", padx=10, pady=6)

        self._flex_labels = []
        for i, (label, gpio) in enumerate([("Flex 0 — GPIO 0 (LEFT)", 0),
                                           ("Flex 1 — GPIO 1 (RIGHT)", 1)]):
            col = tk.Frame(flex_inner, bg=C["panel"])
            col.pack(side="left", expand=True, fill="x", padx=(0,16))

            tk.Label(col, text=label, bg=C["panel"],
                     fg=C["text"], font=FONT_BODY).pack(anchor="w")

            sl = tk.Scale(
                col, variable=self.flex_vals[i],
                from_=0.0, to=1.0, resolution=0.01,
                orient="horizontal", length=220,
                bg=C["panel"], fg=C["text"],
                troughcolor=C["panel_dark"],
                highlightthickness=0, bd=0,
                sliderlength=18, command=lambda *_: self._redraw()
            )
            sl.pack(fill="x")

            lbl = tk.Label(col, text="Plano", bg=C["panel"],
                           fg=C["text_dim"], font=FONT_SMALL)
            lbl.pack(anchor="w")
            self._flex_labels.append(lbl)

        #  Botões simulados
        btn_card = tk.LabelFrame(
            self, text=" BOTÕES FÍSICOS ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove"
        )
        btn_card.pack(fill="x", padx=8, pady=(0,8))

        btn_inner = tk.Frame(btn_card, bg=C["panel"])
        btn_inner.pack(padx=10, pady=6)

        for text, var, color in [
            ("BACK  (GPIO 2)",    self.btn_back,   C["btn"]),
            ("FORWARD (GPIO 3)",  self.btn_fwd,    C["btn"]),
            ("SCROLL (GPIO 9)",   self.btn_scroll, C["accent"]),
        ]:
            cb = tk.Checkbutton(
                btn_inner, text=text, variable=var,
                bg=C["panel"], fg=C["text"],
                selectcolor=C["panel_dark"],
                activebackground=C["panel"],
                activeforeground=C["accent2"],
                font=FONT_BODY,
                command=self._redraw
            )
            cb.pack(side="left", padx=12)

        # ── Status ao vivo ─────────────────────
        status_card = tk.LabelFrame(
            self, text=" ESTADO AO VIVO ", bg=C["panel"],
            fg=C["accent"], font=FONT_TITLE,
            bd=2, relief="groove"
        )
        status_card.pack(fill="x", padx=8, pady=(0,8))

        self.status_lbl = tk.Label(
            status_card,
            text="Conecte ao ESP32 para ver dados reais",
            bg=C["panel"], fg=C["text_dim"], font=FONT_MONO
        )
        self.status_lbl.pack(padx=10, pady=6)

        self._redraw()

    # ── Desenho da mão ─────────────────────────
    def _redraw(self):
        self._draw_hand()
        self._draw_mpu()
        self._update_flex_labels()

    def _draw_hand(self):
        c = self.canvas
        c.delete("all")
        W, H = 260, 280

        # Palma
        palm_x, palm_y = 100, 190
        palm_w, palm_h = 90, 80
        c.create_oval(
            palm_x - palm_w//2, palm_y - palm_h//2,
            palm_x + palm_w//2, palm_y + palm_h//2,
            fill=C["btn"], outline=C["border_hi"], width=2
        )

        # Configurações dos dedos
        finger_configs = [
            # (offset_x, base_y, label, flex_idx or None)
            (-48, 155, "M", None),   # mindinho
            (-22, 135, "A", None),   # anelar
            (  4, 125, "R", None),   # médio (referência)
            ( 30, 135, "F", 1),      # indicador → flex[1] RIGHT
            ( 58, 155, "P", 0),      # polegar   → flex[0] LEFT
        ]

        for ox, base_y, lbl, flex_idx in finger_configs:
            fx = 1.0 if flex_idx is not None else 0.0
            if flex_idx is not None:
                fx = self.flex_vals[flex_idx].get()

            # Cor do dedo baseada na curvatura
            r = int(0x5C + fx * (0xA0 - 0x5C))
            g = int(0x6B + fx * (0x30 - 0x6B))
            b_c = int(0x54 + fx * (0x30 - 0x54))
            color = f"#{r:02X}{g:02X}{b_c:02X}"

            # Posição com curvatura (dedo dobra para baixo)
            x = palm_x + ox
            bend = fx * 55    # quanto o dedo "desce"
            top_y = base_y - int((1.0 - fx) * 60)

            # Segmento do dedo
            c.create_line(
                x, base_y, x, top_y,
                fill=color, width=14, capstyle="round"
            )

            # Ponta do dedo
            tip_color = C["accent"] if (flex_idx is not None and fx > 0.5) else C["border_hi"]
            c.create_oval(
                x-7, top_y-7, x+7, top_y+7,
                fill=tip_color, outline=C["border"]
            )

            
            c.create_text(x, top_y, text=lbl,
                          fill=C["text"], font=("Tahoma",7,"bold"))

        # Legenda
        c.create_text(10, 265, anchor="w",
                      text="● Polegar=LEFT  ○ Indicador=RIGHT",
                      fill=C["text_dim"], font=("Tahoma",7))

        # Estado dos botões na palma
        states = []
        if self.btn_back.get():   states.append("BACK")
        if self.btn_fwd.get():    states.append("FWD")
        if self.btn_scroll.get(): states.append("SCROLL")
        if states:
            c.create_text(
                palm_x, palm_y,
                text=" + ".join(states),
                fill=C["accent"], font=("Tahoma",8,"bold")
            )

    def _draw_mpu(self):
        c = self.mpu_canvas
        c.delete("all")
        W = H = 140
        cx = cy = 70
        r = 50

        # Círculo de fundo
        c.create_oval(cx-r,cy-r,cx+r,cy+r,
                      outline=C["border_hi"], width=1, fill=C["panel_dark"])

        # Cruz de referência
        c.create_line(cx-r,cy,cx+r,cy, fill=C["border_hi"], width=1, dash=(2,4))
        c.create_line(cx,cy-r,cx,cy+r, fill=C["border_hi"], width=1, dash=(2,4))

        # Posição da bola baseada em pitch e roll
        pitch = self.pitch_var.get()
        roll  = self.roll_var.get()
        bx = cx + (roll  / 90.0) * r * 0.9
        by = cy + (pitch / 90.0) * r * 0.9

        # Sombra
        c.create_oval(bx-12,by-12,bx+12,by+12,
                      fill=C["border"], outline="")
        # Bola
        c.create_oval(bx-10,by-10,bx+10,by+10,
                      fill=C["accent"], outline=C["border_hi"], width=2)

        # Labels
        c.create_text(cx, cy-r-8, text="PITCH/ROLL",
                      fill=C["text_dim"], font=("Tahoma",7))
        c.create_text(cx, cy+r+8,
                      text=f"P={pitch:.0f}° R={roll:.0f}°",
                      fill=C["accent"], font=FONT_MONO)

    def _update_flex_labels(self):
        names = [("Plano","Dobrado"),("Plano","Dobrado")]
        for i, lbl in enumerate(self._flex_labels):
            v = self.flex_vals[i].get()
            if v < 0.25:
                text, color = "● Plano", C["text_dim"]
            elif v < 0.5:
                text, color = "◑ Semi-dobrado", C["yellow"]
            else:
                text, color = "● Dobrado (ativo)", C["green_hi"]
            lbl.config(text=f"{text}  ({v:.2f})", fg=color)

    def update_live_sensors(self, data: dict):
        """Atualiza os controles com dados reais do ESP32."""
        try:
            self.pitch_var.set(round(data.get("pitch", 0), 1))
            self.roll_var.set(round(data.get("roll", 0), 1))
            self.flex_vals[0].set(round(data.get("flex0", 0), 3))
            self.flex_vals[1].set(round(data.get("flex1", 0), 3))
            self.btn_back.set(bool(data.get("btn_back", 0)))
            self.btn_fwd.set(bool(data.get("btn_fwd", 0)))
            self.status_lbl.config(
                text=(f"pitch={data['pitch']:.1f}°  roll={data['roll']:.1f}°  "
                      f"gx={data.get('gx',0):.1f}  gy={data.get('gy',0):.1f}  "
                      f"flex=[{data['flex0']:.2f},{data['flex1']:.2f}]"),
                fg=C["text"]
            )
            self._redraw()
        except: pass


# ════════════════════════════════════════════════
#  JANELA PRINCIPAL
# ════════════════════════════════════════════════
class RANDApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RAND Criador de gestos    by Capapesto")
        self.geometry("900x680")
        self.resizable(True, True)
        self.configure(bg=C["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.sm = SerialManager(self._on_serial_line, self._on_serial_state)
        self._build()
        self._auto_refresh_id = None

    def _build(self):
        # ── Barra de título customizada ────────
        titlebar = tk.Frame(self, bg=C["titlebar"], height=36)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)

        tk.Label(
            titlebar, text="  ◈ RAND  ",
            bg=C["titlebar"], fg=C["accent"], font=FONT_BIG
        ).pack(side="left", padx=8, pady=4)

        tk.Label(
            titlebar, text="Reconfigurable Articulated Node Driver",
            bg=C["titlebar"], fg=C["text_dim"], font=FONT_SMALL
        ).pack(side="left", pady=4)

        # ── Barra de conexão ───────────────────
        conn_bar = tk.Frame(self, bg=C["panel_dark"], height=38)
        conn_bar.pack(fill="x")
        conn_bar.pack_propagate(False)

        tk.Label(conn_bar, text="  Porta:", bg=C["panel_dark"],
                 fg=C["text"], font=FONT_BODY).pack(side="left")

        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(
            conn_bar, textvariable=self.port_var,
            width=14, font=FONT_BODY, state="readonly"
        )
        self.port_box.pack(side="left", padx=(4,8), pady=5)

        xp_btn(conn_bar, "↻", self._refresh_ports, width=2).pack(side="left")

        self.conn_btn = xp_btn(conn_bar, "Conectar", self._toggle_connect,
                                C["accent"], width=10)
        self.conn_btn.pack(side="left", padx=(8,0))

        self.conn_status = tk.Label(
            conn_bar, text="● Desconectado",
            bg=C["panel_dark"], fg=C["log_err"], font=FONT_BODY
        )
        self.conn_status.pack(side="left", padx=12)

        # ── Notebook (abas) ────────────────────
        style = ttk.Style()
        style.theme_use("default")
        style.configure("RAND.TNotebook",
                        background=C["bg"],
                        borderwidth=0)
        style.configure("RAND.TNotebook.Tab",
                        background=C["btn"],
                        foreground=C["text"],
                        font=FONT_TITLE,
                        padding=[16, 6])
        style.map("RAND.TNotebook.Tab",
                  background=[("selected", C["accent"])],
                  foreground=[("selected", C["text"])])

        self.nb = ttk.Notebook(self, style="RAND.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tab_gesture = GestureManagerTab(self.nb, self.sm)
        self.tab_finger  = FingerSimulatorTab(self.nb, self.sm)

        self.nb.add(self.tab_gesture, text="  ✋ Gesture Manager  ")
        self.nb.add(self.tab_finger,  text="  ☝ Finger Simulator  ")

        self._refresh_ports()

    # ── Conexão ────────────────────────────────
    def _refresh_ports(self):
        ports = self.sm.list_ports()
        self.port_box["values"] = ports
        if ports: self.port_var.set(ports[0])

    def _toggle_connect(self):
        if self.sm.ser and self.sm.ser.is_open:
            self.sm.disconnect()
        else:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("RAND", "Selecione uma porta serial.")
                return
            try:
                self.sm.connect(port)
            except Exception as e:
                messagebox.showerror("Erro de conexão", str(e))

    def _on_serial_state(self, connected: bool):
        """Chamado da thread serial — agenda update na thread UI."""
        self.after(0, self._update_conn_ui, connected)

    def _update_conn_ui(self, connected: bool):
        if connected:
            self.conn_status.config(text="● Conectado", fg=C["green_hi"])
            self.conn_btn.config(text="Desconectar", bg=C["red"])
            # Solicita lista de gestos ao conectar
            self.after(800, self.tab_gesture._refresh)
        else:
            self.conn_status.config(text="● Desconectado", fg=C["log_err"])
            self.conn_btn.config(text="Conectar", bg=C["accent"])

    def _on_serial_line(self, line: str):
        """Recebe linha do ESP32 e distribui para as abas."""
        self.after(0, self._dispatch_line, line)

    def _dispatch_line(self, line: str):
        # Atualiza gesture manager
        self.tab_gesture.on_serial_line(line)

        # Atualiza finger simulator se for dado de sensores
        if line.startswith("SENSORS:"):
            try:
                data = json.loads(line[8:])
                self.tab_finger.update_live_sensors(data)
            except: pass

    def _on_close(self):
        if self.sm.ser and self.sm.ser.is_open:
            self.sm.disconnect()
        self.destroy()


# ════════════════════════════════════════════════
#  ENTRY POINT
# ════════════════════════════════════════════════
if __name__ == "__main__":
    app = RANDApp()
    app.mainloop()
