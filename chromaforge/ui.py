"""CustomTkinter application shell, authentication and common UI services."""
from __future__ import annotations

import logging
import queue
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk
from pymongo.errors import PyMongoError

from .database import Store

logging.basicConfig(filename=str(Path(tempfile.gettempdir()) / "chromaforge.log"), level=logging.ERROR,
                    format="%(asctime)s %(levelname)s %(message)s")

BG = "#0B1020"
SIDE = "#111827"
PANEL = "#1B2435"
ELEV = "#273449"
ACCENT = "#8B5CF6"
CYAN = "#06B6D4"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
ERROR = "#EF4444"


def label(parent, text, size=14, color=TEXT, weight="normal", **kwargs):
    return ctk.CTkLabel(parent, text=text, text_color=color, font=("Segoe UI", size, weight), **kwargs)


def button(parent, text, command, color=ACCENT, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command, fg_color=color, hover_color=ELEV if color != ELEV else ACCENT,
                         text_color=TEXT, corner_radius=10, font=("Segoe UI", 13, "bold"), height=38, **kwargs)


def card(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=14, **kwargs)


class ChromaForgeApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("ChromaForge — Color Studio")
        self.geometry("1440x900")
        self.minsize(1050, 700)
        self.update_idletasks()
        self.geometry(f"1440x900+{max(0,(self.winfo_screenwidth()-1440)//2)}+{max(0,(self.winfo_screenheight()-900)//2)}")
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.store = Store()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chromaforge")
        self._results = queue.Queue()
        self.user = None
        self.current_color = "#8B5CF6"
        self.editing_palette = None
        self.editing_gradient = None
        self.page_name = ""
        self._toast_job = None
        self.bind("<Control-Shift-C>", lambda _: self.copy(self.current_color))
        self.bind("<Control-s>", lambda _: self.save_current_color() if self.user else None)
        self.bind("<Control-o>", lambda _: self.navigate("Image Extractor") if self.user else None)
        self.splash()
        self.after(40, self._drain_results)
        self.after(650, self.check_database)

    def clear(self):
        for child in self.winfo_children():
            child.destroy()

    def run_task(self, operation, success=None, failure=None):
        future = self.executor.submit(operation)
        def complete(done):
            try:
                result = done.result()
            except Exception as exc:
                logging.exception("Background operation failed", exc_info=exc)
                self._results.put((False, exc, failure))
            else:
                self._results.put((True, result, success))
        future.add_done_callback(complete)

    def _drain_results(self):
        while True:
            try:
                ok, value, callback = self._results.get_nowait()
            except queue.Empty:
                break
            if ok:
                if callback: callback(value)
            elif callback:
                callback(value)
            else:
                self.show_error(value)
        if self.winfo_exists():
            self.after(40, self._drain_results)

    def show_error(self, exc):
        if isinstance(exc, (PyMongoError, ConnectionError)):
            self.connection_error()
        else:
            messagebox.showerror("ChromaForge", str(exc), parent=self)

    def splash(self):
        self.clear()
        frame = ctk.CTkFrame(self, fg_color=BG)
        frame.pack(expand=True)
        ctk.CTkFrame(frame, width=56, height=56, fg_color=ACCENT, corner_radius=16).pack(pady=(0, 20))
        label(frame, "ChromaForge", 42, TEXT, "bold").pack()
        label(frame, "A workspace for color in every form", 17, MUTED).pack(pady=(12, 28))
        ctk.CTkProgressBar(frame, width=260, progress_color=ACCENT).pack()

    def check_database(self):
        self.run_task(self.store.connect, lambda _: self.auth_screen(), lambda _: self.connection_error())

    def connection_error(self):
        self.clear()
        frame = card(self, width=530)
        frame.pack(expand=True)
        frame.pack_propagate(False)
        frame.configure(height=310)
        label(frame, "Database connection unavailable", 27, TEXT, "bold").pack(padx=35, pady=(35, 12))
        label(frame, "Start your local MongoDB service, then select Retry.\nChromaForge uses mongodb://localhost:27017/", 15, MUTED, justify="center").pack(pady=10)
        button(frame, "Retry connection", lambda: (self.splash(), self.check_database())).pack(pady=22)
        label(frame, "Your saved data stays on this computer.", 12, MUTED).pack()

    def auth_screen(self, register=False):
        self.clear()
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(fill="both", expand=True)
        brand = ctk.CTkFrame(wrapper, fg_color=SIDE, width=480, corner_radius=0)
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)
        label(brand, "CHROMAFORGE", 25, TEXT, "bold").pack(anchor="w", padx=52, pady=(72, 0))
        label(brand, "Shape color.\nKeep inspiration.", 37, TEXT, "bold", justify="left").pack(anchor="w", padx=52, pady=(110, 16))
        label(brand, "Pick precise colors, build palettes, and\nkeep every useful discovery in one place.", 17, MUTED, justify="left").pack(anchor="w", padx=52)
        swatches = ctk.CTkFrame(brand, fg_color="transparent")
        swatches.pack(anchor="w", padx=52, pady=52)
        for color in ("#8B5CF6", "#06B6D4", "#F59E0B", "#EF4444", "#22C55E"):
            ctk.CTkFrame(swatches, width=60, height=100, fg_color=color, corner_radius=4).pack(side="left", padx=2)
        form = ctk.CTkFrame(wrapper, fg_color="transparent")
        form.pack(side="left", fill="both", expand=True)
        inner = ctk.CTkFrame(form, fg_color="transparent", width=430)
        inner.place(relx=.5, rely=.5, anchor="center")
        label(inner, "Create your account" if register else "Welcome back", 32, TEXT, "bold").pack(anchor="w", pady=(0, 8))
        label(inner, "Make room for your next idea." if register else "Sign in to your color workspace.", 15, MUTED).pack(anchor="w", pady=(0, 28))
        fields = {}
        names = (["Full name", "Username", "Email", "Password", "Confirm password"] if register else ["Username or email", "Password"])
        for name in names:
            label(inner, name, 13, MUTED).pack(anchor="w", pady=(10, 5))
            entry = ctk.CTkEntry(inner, width=390, height=42, fg_color=PANEL, border_color=ELEV,
                                 show="●" if "password" in name.lower() else "")
            entry.pack(anchor="w")
            fields[name] = entry
        show_var = ctk.BooleanVar(value=False)
        def toggle():
            for key, entry in fields.items():
                if "password" in key.lower():
                    entry.configure(show="" if show_var.get() else "●")
        ctk.CTkCheckBox(inner, text="Show password", variable=show_var, command=toggle, fg_color=ACCENT).pack(anchor="w", pady=(15, 5))
        status = label(inner, "", 13, ERROR)
        status.pack(anchor="w", pady=(5, 0))
        def submit():
            values = {k: e.get() for k, e in fields.items()}
            if register and values["Password"] != values["Confirm password"]:
                status.configure(text="Passwords do not match.")
                return
            action.configure(state="disabled", text="Please wait…")
            operation = (lambda: self.store.register(values["Full name"], values["Username"], values["Email"], values["Password"])) if register else (lambda: self.store.login(values["Username or email"], values["Password"]))
            def failed(exc):
                action.configure(state="normal", text="Create account" if register else "Sign in")
                if isinstance(exc, PyMongoError):
                    self.connection_error()
                else:
                    status.configure(text=str(exc))
            self.run_task(operation, self.enter_dashboard, failed)
        action = button(inner, "Create account" if register else "Sign in", submit, width=390)
        action.pack(anchor="w", pady=(17, 12))
        button(inner, "Already have an account? Sign in" if register else "New here? Create an account",
               lambda: self.auth_screen(not register), color=ELEV, width=390).pack(anchor="w")
        fields[names[0]].focus_set()
        self.bind("<Return>", lambda _: submit())

    def enter_dashboard(self, user):
        self.unbind("<Return>")
        self.user = user
        ctk.set_appearance_mode(user.get("preferences", {}).get("theme", "dark"))
        self.navigate("Dashboard")
        self.toast("Welcome to ChromaForge")

    def navigate(self, name):
        from . import pages
        if not self.user:
            return
        self.page_name = name
        self.clear()
        shell = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        shell.pack(fill="both", expand=True)
        sidebar = ctk.CTkFrame(shell, width=235, fg_color=SIDE, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        label(sidebar, "ChromaForge", 22, TEXT, "bold").pack(anchor="w", padx=22, pady=(28, 22))
        nav_frame = ctk.CTkScrollableFrame(sidebar, fg_color=SIDE, corner_radius=0)
        nav_frame.pack(fill="both", expand=True)
        nav = ["Dashboard", "Color Picker", "Palette Generator", "Image Extractor", "Gradient Studio", "Contrast Checker", "Saved Collections", "Color History", "Settings & Profile"]
        for item in nav:
            selected = item == name
            button(nav_frame, item, lambda n=item: self.navigate(n), color=ACCENT if selected else SIDE,
                   width=185, anchor="w").pack(padx=7, pady=2)
        label(sidebar, self.user["full_name"], 14, TEXT, "bold").pack(anchor="w", padx=22)
        label(sidebar, "@" + self.user["username"], 12, MUTED).pack(anchor="w", padx=22, pady=(0, 10))
        button(sidebar, "Log out", self.logout, color=ELEV, width=195).pack(padx=20, pady=(0, 24))
        right = ctk.CTkFrame(shell, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)
        top = ctk.CTkFrame(right, fg_color=BG, height=77, corner_radius=0)
        top.pack(fill="x")
        label(top, name, 26, TEXT, "bold").pack(side="left", padx=32, pady=20)
        label(top, datetime.now().strftime("%A, %d %B"), 13, MUTED).pack(side="right", padx=32)
        area = ctk.CTkScrollableFrame(right, fg_color=BG, corner_radius=0)
        area.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        pages.render(self, area, name)

    def toast(self, message):
        if getattr(self, "_toast", None) and self._toast.winfo_exists():
            self._toast.destroy()
        self._toast = ctk.CTkLabel(self, text=message, fg_color=ELEV, text_color=TEXT, corner_radius=10, padx=18, pady=10)
        self._toast.place(relx=.98, rely=.97, anchor="se")
        self._toast_job = self.after(2700, lambda: self._toast.destroy() if self._toast.winfo_exists() else None)

    def copy(self, value):
        self.clipboard_clear()
        self.clipboard_append(value)
        self.toast("Copied to clipboard")

    def save_current_color(self):
        if self.user:
            from . import pages
            pages.save_color_dialog(self, self.current_color)

    def logout(self):
        self.user = None
        self.current_color = "#8B5CF6"
        self.auth_screen()

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.store.close()
        self.destroy()
