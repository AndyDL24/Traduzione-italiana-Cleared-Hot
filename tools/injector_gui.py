# -*- coding: utf-8 -*-
"""Injector one-click per Cleared Hot — traduzione italiana nello slot Francese."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# permette import da stessa cartella
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import injector_core as core  # noqa: E402


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Cleared Hot — Traduzione Italiana (Injector)")
        self.geometry("720x520")
        self.minsize(640, 440)

        self.game_var = tk.StringVar()
        self.txt_var = tk.StringVar(value=str(core.default_translation_path()))
        self.rename_var = tk.BooleanVar(value=True)
        self._busy = False

        self._build()
        self.after(100, self._autodetect)

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, **pad)

        ttk.Label(frm, text="Cartella ClearedHot_Data (o root del gioco)").pack(anchor=tk.W)
        row1 = ttk.Frame(frm)
        row1.pack(fill=tk.X, pady=(0, 6))
        ttk.Entry(row1, textvariable=self.game_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row1, text="Sfoglia…", command=self._browse_game).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(row1, text="Rileva Steam", command=self._autodetect).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(frm, text="File traduzione Unity (.txt)").pack(anchor=tk.W)
        row2 = ttk.Frame(frm)
        row2.pack(fill=tk.X, pady=(0, 6))
        ttk.Entry(row2, textvariable=self.txt_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row2, text="Sfoglia…", command=self._browse_txt).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Checkbutton(
            frm,
            text='Rinomina voce menu "Français" → "Italiano"',
            variable=self.rename_var,
        ).pack(anchor=tk.W)

        self.status = ttk.Label(frm, text="Pronto.", foreground="#333")
        self.status.pack(anchor=tk.W, pady=(4, 4))

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=6)
        self.btn_install = ttk.Button(btns, text="Installa traduzione", command=self._install)
        self.btn_install.pack(side=tk.LEFT)
        self.btn_verify = ttk.Button(btns, text="Verifica", command=self._verify)
        self.btn_verify.pack(side=tk.LEFT, padx=6)
        self.btn_restore = ttk.Button(btns, text="Ripristina originale", command=self._restore)
        self.btn_restore.pack(side=tk.LEFT)

        ttk.Label(frm, text="Log").pack(anchor=tk.W)
        self.log = scrolledtext.ScrolledText(frm, height=16, wrap=tk.WORD, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)

        tip = (
            "Dopo l'installazione: avvia Cleared Hot → Impostazioni → Lingua → Italiano "
            "(ex Francese). Chiudi il gioco prima di installare/ripristinare."
        )
        ttk.Label(frm, text=tip, wraplength=680).pack(anchor=tk.W, pady=(6, 0))

    def _append(self, msg: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for b in (self.btn_install, self.btn_verify, self.btn_restore):
            b.configure(state=state)

    def _assets(self) -> Path | None:
        data = core.find_game_data_dir(Path(self.game_var.get().strip()) if self.game_var.get().strip() else None)
        if not data:
            return None
        # aggiorna campo se rilevato
        self.game_var.set(str(data))
        return data / core.ASSET_NAME

    def _autodetect(self) -> None:
        data = core.find_game_data_dir()
        if data:
            self.game_var.set(str(data))
            self.status.configure(text=core.status_summary(data / core.ASSET_NAME))
            self._append(f"Rilevato: {data}")
        else:
            self.status.configure(text="Gioco non trovato automaticamente — usa Sfoglia.")
            self._append("Steam/Cleared Hot non trovato. Seleziona la cartella manualmente.")

    def _browse_game(self) -> None:
        path = filedialog.askdirectory(title="Seleziona ClearedHot o ClearedHot_Data")
        if path:
            data = core.find_game_data_dir(Path(path))
            if data:
                self.game_var.set(str(data))
                self.status.configure(text=core.status_summary(data / core.ASSET_NAME))
            else:
                messagebox.showerror("Errore", "Nella cartella non c'è resources.assets")

    def _browse_txt(self) -> None:
        path = filedialog.askopenfilename(
            title="File traduzione",
            filetypes=[("Unity strings", "*.txt"), ("Tutti", "*.*")],
        )
        if path:
            self.txt_var.set(path)

    def _run_bg(self, fn) -> None:
        if self._busy:
            return

        def worker():
            self._set_busy(True)
            try:
                fn()
            finally:
                self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _ui_error(self, title: str, msg: str) -> None:
        self.after(0, lambda: messagebox.showerror(title, msg))

    def _ui_info(self, title: str, msg: str) -> None:
        self.after(0, lambda: messagebox.showinfo(title, msg))

    def _ui_warn(self, title: str, msg: str) -> None:
        self.after(0, lambda: messagebox.showwarning(title, msg))

    def _install(self) -> None:
        def job():
            assets = self._assets()
            if not assets:
                self._ui_error("Errore", "Seleziona una cartella di gioco valida.")
                return
            txt = Path(self.txt_var.get().strip())
            self.after(0, self._append, "--- Installazione ---")
            try:
                res = core.inject_italian(
                    assets,
                    txt,
                    rename_fr_label=self.rename_var.get(),
                    log=lambda m: self.after(0, self._append, m),
                )
            except Exception as e:
                self.after(0, self._append, f"ERRORE: {e}")
                self._ui_error("Errore", str(e))
                return
            self.after(0, lambda: self.status.configure(text=res.message))
            if res.ok:
                self._ui_info(
                    "OK",
                    "Traduzione installata.\n\nNel gioco scegli la lingua «Italiano» "
                    "(sostituisce il Francese).",
                )
            else:
                self._ui_error("Fallito", res.message)

        self._run_bg(job)

    def _verify(self) -> None:
        def job():
            assets = self._assets()
            if not assets:
                self._ui_error("Errore", "Seleziona una cartella di gioco valida.")
                return
            self.after(0, self._append, "--- Verifica ---")
            res = core.verify_injection(assets, log=lambda m: self.after(0, self._append, m))
            self.after(0, lambda: self.status.configure(text=res.message))
            self.after(0, self._append, core.status_summary(assets))
            if res.ok:
                self._ui_info("Verifica", res.message)
            else:
                self._ui_warn("Verifica", res.message)

        self._run_bg(job)

    def _restore(self) -> None:
        if not messagebox.askyesno(
            "Conferma",
            "Ripristinare resources.assets dal backup creato all'installazione?",
        ):
            return

        def job():
            assets = self._assets()
            if not assets:
                self._ui_error("Errore", "Seleziona una cartella di gioco valida.")
                return
            self.after(0, self._append, "--- Ripristino ---")
            res = core.restore_backup(assets, log=lambda m: self.after(0, self._append, m))
            self.after(0, lambda: self.status.configure(text=res.message))
            if res.ok:
                self._ui_info("OK", res.message)
            else:
                self._ui_error("Errore", res.message)

        self._run_bg(job)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
