"""ChromaForge feature pages. All widgets are constructed on the Tk main thread."""
from __future__ import annotations

import colorsys
import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, colorchooser, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from .color_math import (normalize_hex, hex_to_rgb, rgb_to_hex, hsv, hsl, from_hsv, from_hsl,
                         cmyk, closest_name, contrast, harmony, gradient_image)
from .files import extract_colors, export_palette, validate_palette_json
from .ui import BG, PANEL, ELEV, ACCENT, CYAN, TEXT, MUTED, ERROR, label, button, card


def heading(parent, title, subtitle=""):
    label(parent, title, 23, TEXT, "bold").pack(anchor="w", padx=8, pady=(10, 4))
    if subtitle:
        label(parent, subtitle, 14, MUTED).pack(anchor="w", padx=8, pady=(0, 20))


def row(parent):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=5)
    return frame


def swatch(parent, color, width=100, height=80):
    return ctk.CTkFrame(parent, fg_color=color, width=width, height=height, corner_radius=10)


def prompt(app, title, default=""):
    dialog = ctk.CTkInputDialog(title=title, text=title)
    if default:
        dialog._entry.insert(0, default)
    return dialog.get_input()


def save_color_dialog(app, color, favorite=False):
    name = prompt(app, "Name this color", closest_name(color))
    if name is None:
        return
    name = name.strip() or color
    app.run_task(lambda: app.store.add("saved_colors", app.user["_id"], {
        "name": name, "hex": normalize_hex(color), "rgb": list(hex_to_rgb(color)), "description": "",
        "tags": [], "collection_name": "", "is_favorite": favorite}),
        lambda _: app.toast("Color saved"))


def add_to_palette(app, color):
    window = ctk.CTkToplevel(app)
    window.title("Add color to palette")
    window.geometry("360x400")
    window.configure(fg_color=BG)
    window.transient(app)
    label(window,"Choose a palette",20,TEXT,"bold").pack(anchor="w",padx=20,pady=18)
    content = ctk.CTkScrollableFrame(window,fg_color=BG)
    content.pack(fill="both",expand=True,padx=12,pady=5)
    def show(items):
        if not window.winfo_exists():return
        if not items: label(content,"No saved palettes yet.",14,MUTED).pack(pady=20)
        for item in items:
            def select(target=item):
                fields = {"colors": target["colors"] + [normalize_hex(color)]}
                app.run_task(lambda:app.store.update("palettes",app.user["_id"],target["_id"],fields),lambda _:(window.destroy(),app.toast("Color added to palette")))
            button(content,item["name"],select,color=ELEV).pack(fill="x",pady=4)
    app.run_task(lambda:app.store.list("palettes",app.user["_id"]),show)


def screen_pick(app, on_color):
    """Capture the desktop, then select one pixel from a Tk overlay."""
    app.iconify()
    def capture():
        import mss
        with mss.mss() as session:
            monitor = session.monitors[0]
            shot = session.grab(monitor)
            return Image.frombytes("RGB", shot.size, shot.rgb), monitor
    def show(result):
        image, monitor = result
        app.deiconify()
        overlay = tk.Toplevel(app)
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.geometry(f"{image.width}x{image.height}{monitor['left']:+d}{monitor['top']:+d}")
        canvas = tk.Canvas(overlay, width=image.width, height=image.height, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas._photo = ImageTk.PhotoImage(image)
        canvas.create_image(0,0,anchor="nw",image=canvas._photo)
        hint = canvas.create_text(22,20,anchor="nw",text="Click a pixel to pick · Esc to cancel",fill="white",font=("Segoe UI",14,"bold"))
        def select(event):
            x,y = min(image.width-1,max(0,event.x)),min(image.height-1,max(0,event.y))
            color = rgb_to_hex(image.getpixel((x,y)))
            overlay.destroy()
            on_color(color)
            commit_color(app,color,"screen")
            app.toast(f"Picked {color}")
        canvas.bind("<Button-1>",select)
        overlay.bind("<Escape>",lambda _:overlay.destroy())
        overlay.focus_force()
    def failed(exc):
        app.deiconify()
        messagebox.showerror("Screen picker", f"Screen capture is unavailable: {exc}\nUse the Image Extractor as an alternative.",parent=app)
    app.after(500,lambda:app.run_task(capture,show,failed))


def commit_color(app, color, source):
    color = normalize_hex(color)
    app.current_color = color
    app.run_task(lambda: app.store.history(app.user["_id"], color, source))


def render(app, parent, name):
    mapping = {
        "Dashboard": dashboard, "Color Picker": picker, "Palette Generator": palettes,
        "Image Extractor": image_extractor, "Gradient Studio": gradients,
        "Contrast Checker": contrast_page, "Saved Collections": collections,
        "Color History": history_page, "Settings & Profile": settings,
    }
    mapping[name](app, parent)


def dashboard(app, parent):
    heading(parent, f"Welcome back, {app.user['full_name'].split()[0]}!", "Your color workspace is ready.")
    stats_frame = row(parent)
    for key, title in (("colors", "Saved colors"), ("palettes", "Palettes"), ("picked_today", "Picked today"), ("favorites", "Favorites")):
        tile = card(stats_frame)
        tile.pack(side="left", fill="x", expand=True, padx=5)
        number = label(tile, "—", 29, TEXT, "bold")
        number.pack(anchor="w", padx=20, pady=(17, 0))
        label(tile, title, 13, MUTED).pack(anchor="w", padx=20, pady=(0, 17))
        app.run_task(lambda k=key: app.store.stats(app.user["_id"])[k],
                     lambda value, target=number: target.configure(text=str(value)) if target.winfo_exists() else None)
    day_colors = ["#8B5CF6", "#06B6D4", "#E879F9", "#F59E0B", "#22C55E", "#EF4444"]
    from datetime import date
    today = day_colors[date.today().toordinal() % len(day_colors)]
    featured = card(parent)
    featured.pack(fill="x", padx=5, pady=20)
    swatch(featured, today, 160, 110).pack(side="left", padx=20, pady=20)
    detail = ctk.CTkFrame(featured, fg_color="transparent")
    detail.pack(side="left", padx=10)
    label(detail, "Color of the day", 14, MUTED).pack(anchor="w")
    label(detail, today, 25, TEXT, "bold").pack(anchor="w")
    button(detail, "Use this color", lambda: (setattr(app, "current_color", today), app.navigate("Color Picker"))).pack(anchor="w", pady=(10, 0))
    quick = row(parent)
    for title, target in (("Pick a color", "Color Picker"), ("Build a palette", "Palette Generator"), ("Extract an image", "Image Extractor")):
        button(quick, title, lambda n=target: app.navigate(n), color=ELEV).pack(side="left", padx=5)
    heading(parent, "Recent colors")
    recent = row(parent)
    def show(items):
        if not recent.winfo_exists(): return
        if not items:
            label(recent, "Your selections will appear here as you work.", 14, MUTED).pack(padx=8)
        for item in items[:10]:
            tile = card(recent)
            tile.pack(side="left", padx=5)
            swatch(tile, item["hex"], 68, 48).pack(padx=8, pady=(8, 2))
            button(tile, item["hex"], lambda c=item["hex"]: (setattr(app, "current_color", c), app.navigate("Color Picker")), color=ELEV, width=90).pack(padx=4, pady=4)
    app.run_task(lambda: app.store.list("color_history", app.user["_id"], 10), show)
    heading(parent, "Favorite colors")
    favorites = row(parent)
    def show_favorites(items):
        if not favorites.winfo_exists(): return
        chosen = [x for x in items if x.get("is_favorite")][:8]
        if not chosen: label(favorites, "Favorite saved colors will appear here.", 14, MUTED).pack(padx=8)
        for item in chosen:
            button(favorites, item["hex"], lambda c=item["hex"]: app.copy(c), color=item["hex"], width=115).pack(side="left",padx=4)
    app.run_task(lambda: app.store.list("saved_colors",app.user["_id"],100),show_favorites)
    heading(parent, "Recent palettes")
    recent_palettes = row(parent)
    def show_palettes(items):
        if not recent_palettes.winfo_exists(): return
        if not items: label(recent_palettes,"Saved palettes will appear here.",14,MUTED).pack(padx=8)
        for item in items[:3]:
            tile = card(recent_palettes);tile.pack(side="left",padx=5)
            label(tile,item["name"],14,TEXT,"bold").pack(anchor="w",padx=10,pady=(9,0))
            strip = row(tile)
            for color in item["colors"][:5]:
                swatch(strip,color,35,35).pack(side="left",padx=2)
    app.run_task(lambda: app.store.list("palettes",app.user["_id"],3),show_palettes)


def picker(app, parent):
    heading(parent, "Precision color picker", "Tune a color visually or enter exact RGB, HSV, HSL, or HEX values.")
    body = row(parent)
    left = card(body)
    left.pack(side="left", fill="both", expand=True, padx=5)
    right = card(body)
    right.pack(side="left", fill="both", expand=True, padx=5)
    preview = ctk.CTkFrame(left, fg_color=app.current_color, height=160, corner_radius=12)
    preview.pack(fill="x", padx=18, pady=(18, 12))
    preview.pack_propagate(False)
    visual = row(left)
    wheel = tk.Canvas(visual, width=160, height=160, bg=PANEL, highlightthickness=0)
    wheel.pack(side="left", padx=(18, 10), pady=5)
    sv_canvas = tk.Canvas(visual, width=160, height=160, bg=PANEL, highlightthickness=0)
    sv_canvas.pack(side="left", padx=5, pady=5)
    wheel_image = Image.new("RGB", (160, 160), PANEL)
    wheel_pixels = wheel_image.load()
    for wy in range(160):
        for wx in range(160):
            dx, dy = wx-80, wy-80
            radius = math.hypot(dx, dy)
            if 57 <= radius <= 79:
                wheel_pixels[wx,wy] = hex_to_rgb(from_hsv(math.degrees(math.atan2(dy,dx)),100,100))
    wheel._photo = ImageTk.PhotoImage(wheel_image)
    wheel.create_image(0,0,anchor="nw",image=wheel._photo)
    sv_state = {"hue": None}
    def redraw_sv(hue):
        if sv_state["hue"] == hue: return
        sv_state["hue"] = hue
        image = Image.new("RGB",(160,160))
        pixels = image.load()
        for py in range(160):
            for px in range(160):
                pixels[px,py] = hex_to_rgb(from_hsv(hue,px/159*100,(159-py)/159*100))
        sv_canvas._photo = ImageTk.PhotoImage(image)
        sv_canvas.delete("all")
        sv_canvas.create_image(0,0,anchor="nw",image=sv_canvas._photo)
    def pick_wheel(event):
        dx, dy = event.x-80, event.y-80
        if not 50 <= math.hypot(dx,dy) <= 81: return
        _,sat,val = hsv(app.current_color)
        hue = math.degrees(math.atan2(dy,dx)) % 360
        update(from_hsv(hue,sat,val)); commit_color(app,app.current_color,"color wheel")
    def pick_sv(event):
        hue = hsv(app.current_color)[0]
        update(from_hsv(hue,max(0,min(100,event.x/159*100)),max(0,min(100,(159-event.y)/159*100))))
        commit_color(app,app.current_color,"saturation/value")
    wheel.bind("<Button-1>",pick_wheel)
    sv_canvas.bind("<Button-1>",pick_sv)
    hexline = row(left)
    label(hexline, "HEX", 13, MUTED).pack(side="left", padx=18)
    hex_entry = ctk.CTkEntry(hexline, width=160, fg_color=ELEV, border_width=0)
    hex_entry.pack(side="left", padx=6)
    values = {}
    sync = {"busy": False}
    slider_groups = {}
    def update(color):
        try: color = normalize_hex(color)
        except ValueError: return
        sync["busy"] = True
        app.current_color = color
        preview.configure(fg_color=color)
        hex_entry.delete(0, "end"); hex_entry.insert(0, color)
        rgb = hex_to_rgb(color); h, s, v = hsv(color)
        redraw_sv(h)
        for key, val in zip(("R","G","B","H","S","V"), (*rgb,h,s,v)):
            if key in slider_groups:
                slider_groups[key][0].set(val)
                slider_groups[key][1].configure(text=str(val))
        formats = {"RGB": f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})", "HSV": f"hsv({h}, {s}%, {v}%)",
                   "HSL": f"hsl({hsl(color)[0]}, {hsl(color)[1]}%, {hsl(color)[2]}%)",
                   "CMYK": "cmyk(%d%%, %d%%, %d%%, %d%%)" % cmyk(color), "Name": closest_name(color)}
        for key, value in formats.items():
            values[key].configure(text=value)
        sync["busy"] = False
    def slider_changed(_=None):
        if sync["busy"]: return
        selected = tab.get()
        if selected == "RGB":
            color = rgb_to_hex(tuple(round(slider_groups[x][0].get()) for x in "RGB"))
        else:
            color = from_hsv(*(slider_groups[x][0].get() for x in "HSV"))
        update(color)
    button(hexline, "Apply", lambda: apply_hex(), width=70).pack(side="left", padx=3)
    def apply_hex():
        try:
            update(normalize_hex(hex_entry.get())); commit_color(app, app.current_color, "HEX input")
        except ValueError as exc: app.show_error(exc)
    hex_entry.bind("<Return>", lambda _: apply_hex())
    tab = ctk.CTkSegmentedButton(left, values=["RGB", "HSV"], fg_color=ELEV, selected_color=ACCENT)
    tab.set("RGB"); tab.pack(padx=18, pady=10)
    slider_frame = ctk.CTkFrame(left, fg_color="transparent")
    slider_frame.pack(fill="x", padx=18)
    def draw_sliders(choice):
        for child in slider_frame.winfo_children(): child.destroy()
        slider_groups.clear()
        keys = "RGB" if choice == "RGB" else "HSV"
        for key in keys:
            group = row(slider_frame)
            label(group, key, 13, MUTED, width=28).pack(side="left")
            slider = ctk.CTkSlider(group, from_=0, to=360 if key == "H" else 100 if key in "SV" else 255,
                                   command=slider_changed, progress_color=ACCENT)
            slider.pack(side="left", fill="x", expand=True, padx=10)
            slider.bind("<ButtonRelease-1>", lambda _: commit_color(app, app.current_color, "slider"))
            value = label(group, "0", 12, TEXT, width=30)
            value.pack(side="left")
            slider_groups[key] = slider, value
        update(app.current_color)
    tab.configure(command=draw_sliders)
    actions = row(left)
    button(actions, "Choose color…", lambda: choose(), color=ELEV).pack(side="left", padx=16)
    button(actions, "Save color", lambda: save_color_dialog(app, app.current_color)).pack(side="left")
    button(actions, "Screen pick", lambda: screen_pick(app, update), color=ELEV).pack(side="left", padx=5)
    def choose():
        result = colorchooser.askcolor(color=app.current_color, parent=app)
        if result[1]: update(result[1]); commit_color(app, app.current_color, "color chooser")
    label(left, "Presets", 13, MUTED).pack(anchor="w", padx=18, pady=(16, 4))
    presets = row(left)
    for color in ("#8B5CF6", "#06B6D4", "#F59E0B", "#EF4444", "#22C55E", "#FFFFFF", "#111827"):
        button(presets, "", lambda c=color: (update(c), commit_color(app, c, "preset")), color=color, width=38).pack(side="left", padx=3)
    label(right, "Color values", 19, TEXT, "bold").pack(anchor="w", padx=18, pady=(20, 10))
    for key in ("RGB", "HSV", "HSL", "CMYK", "Name"):
        line = row(right)
        label(line, key, 13, MUTED, width=55).pack(side="left", padx=(18, 4))
        values[key] = label(line, "", 14, TEXT)
        values[key].pack(side="left", fill="x", expand=True)
        if key != "Name":
            button(line, "Copy", lambda k=key: app.copy(values[k].cget("text")), color=ELEV, width=60).pack(side="right", padx=15)
    more = row(right)
    button(more, "Copy HEX", lambda: app.copy(app.current_color)).pack(side="left", padx=17)
    button(more, "Favorite", lambda: save_color_dialog(app, app.current_color, True), color=ELEV).pack(side="left", padx=5)
    button(more, "Add to palette", lambda: add_to_palette(app, app.current_color), color=ELEV).pack(side="left", padx=5)
    button(more, "Check contrast", lambda: app.navigate("Contrast Checker"), color=ELEV).pack(side="left")
    label(right, "HSL input", 13, MUTED).pack(anchor="w", padx=18, pady=(25, 5))
    hsl_row = row(right)
    hsl_entries = []
    for name in ("Hue", "Sat %", "Light %"):
        field = ctk.CTkEntry(hsl_row, width=80, placeholder_text=name, fg_color=ELEV, border_width=0)
        field.pack(side="left", padx=(18 if not hsl_entries else 3, 3)); hsl_entries.append(field)
    def apply_hsl():
        try:
            h, s, l = [float(e.get()) for e in hsl_entries]
            if not (0 <= h <= 360 and 0 <= s <= 100 and 0 <= l <= 100): raise ValueError()
            update(from_hsl(h,s,l)); commit_color(app, app.current_color, "HSL input")
        except ValueError: app.show_error(ValueError("Enter HSL as hue 0–360, saturation 0–100 and lightness 0–100."))
    button(hsl_row, "Apply HSL", apply_hsl, width=95).pack(side="left", padx=4)
    update(app.current_color)
    draw_sliders("RGB")
    for field, number in zip(hsl_entries, hsl(app.current_color)): field.insert(0, str(number))
    heading(parent, "Matching colors")
    matches = row(parent)
    def matching():
        for child in matches.winfo_children(): child.destroy()
        for color in harmony(app.current_color, "Analogous"):
            tile = card(matches); tile.pack(side="left", padx=5)
            swatch(tile, color, 105, 55).pack(padx=7, pady=7)
            button(tile, color, lambda c=color: (update(c), commit_color(app, c, "matching color")), color=ELEV, width=105).pack(padx=5, pady=(0, 5))
    button(parent, "Generate matching colors", matching, color=ELEV).pack(anchor="w", padx=8, pady=8)


def palettes(app, parent):
    heading(parent, "Palette generator", "Build color relationships from a base hue, then refine and save.")
    controls = card(parent); controls.pack(fill="x", padx=5, pady=5)
    line = row(controls)
    base = ctk.CTkEntry(line, width=110, fg_color=ELEV); base.insert(0, app.current_color); base.pack(side="left", padx=18, pady=14)
    kinds = ["Complementary", "Analogous", "Triadic", "Tetradic", "Split complementary", "Monochromatic", "Shades and tints", "Random harmonized"]
    kind = ctk.CTkOptionMenu(line, values=kinds, fg_color=ACCENT); kind.set("Analogous"); kind.pack(side="left", padx=5)
    count = ctk.CTkOptionMenu(line, values=[str(x) for x in range(3, 11)], width=65, fg_color=ELEV); count.set("5"); count.pack(side="left", padx=5)
    colors = []
    locked = set()
    editing = app.editing_palette
    if editing:
        colors[:] = list(editing["colors"])
        base.delete(0,"end"); base.insert(0,colors[0])
        if editing.get("harmony_type") in kinds: kind.set(editing["harmony_type"])
        count.set(str(len(colors)))
    preview = row(parent)
    name = ctk.CTkEntry(parent, width=260, placeholder_text="Palette name", fg_color=ELEV)
    name.pack(anchor="w", padx=8, pady=8)
    if editing: name.insert(0,editing["name"])
    def draw():
        for child in preview.winfo_children(): child.destroy()
        for index, color in enumerate(colors):
            tile = card(preview); tile.pack(side="left", fill="x", expand=True, padx=4)
            swatch(tile, color, 115, 115).pack(fill="x", padx=6, pady=6)
            button(tile, color, lambda c=color: app.copy(c), color=ELEV, width=90).pack(pady=3)
            ctl = row(tile)
            button(ctl, "Unlock" if index in locked else "Lock", lambda i=index: toggle(i), color=ELEV, width=65).pack(side="left", padx=3)
            button(ctl, "Edit", lambda i=index: edit(i), color=ELEV, width=50).pack(side="left", padx=3)
            move = row(tile)
            button(move, "Left", lambda i=index: shift(i,-1), color=ELEV, width=50).pack(side="left", padx=3)
            button(move, "Right", lambda i=index: shift(i,1), color=ELEV, width=50).pack(side="left", padx=3)
    def toggle(i):
        if i in locked: locked.remove(i)
        else: locked.add(i)
        draw()
    def edit(i):
        selected = colorchooser.askcolor(color=colors[i], parent=app)[1]
        if selected: colors[i] = normalize_hex(selected); draw()
    def shift(i, direction):
        target = i + direction
        if 0 <= target < len(colors): colors[i],colors[target] = colors[target],colors[i]; draw()
    def generate():
        try:
            generated = harmony(normalize_hex(base.get()), kind.get(), int(count.get()))
            colors[:] = [colors[i] if i in locked and i < len(colors) else c for i,c in enumerate(generated)]
            draw()
        except ValueError as exc: app.show_error(exc)
    button(line, "Generate", generate).pack(side="left", padx=5)
    def save():
        if not colors: return app.toast("Generate a palette first")
        title = name.get().strip() or f"{kind.get()} palette"
        fields = {"name": title, "colors": colors.copy(), "harmony_type": kind.get()}
        if app.editing_palette:
            app.run_task(lambda: app.store.update("palettes", app.user["_id"], app.editing_palette["_id"], fields), lambda _: app.toast("Palette updated"))
        else:
            app.run_task(lambda: app.store.add("palettes", app.user["_id"], {**fields,"is_favorite": False}), lambda _: app.toast("Palette saved"))
    actions = row(parent)
    button(actions, "Save palette", save).pack(side="left", padx=5)
    button(actions, "Export…", lambda: export_current(app, name.get() or "Palette", colors), color=ELEV).pack(side="left", padx=5)
    button(actions, "Import JSON…", lambda: import_palette(app), color=ELEV).pack(side="left", padx=5)
    if editing:
        button(actions, "New palette", lambda: (setattr(app,"editing_palette",None),app.navigate("Palette Generator")), color=ELEV).pack(side="left",padx=5)
        draw()
    else: generate()


def export_current(app, name, colors):
    if not colors: return app.toast("No colors to export")
    path = filedialog.asksaveasfilename(parent=app, defaultextension=".json", filetypes=[("JSON", "*.json"), ("CSS", "*.css"), ("SCSS", "*.scss"), ("HEX list", "*.txt"), ("GIMP palette", "*.gpl"), ("PNG", "*.png")])
    if path:
        app.run_task(lambda: export_palette(path, name, colors), lambda _: app.toast("Palette exported"))


def import_palette(app):
    path = filedialog.askopenfilename(parent=app, filetypes=[("Palette JSON", "*.json")])
    if path:
        def operation():
            item = validate_palette_json(Path(path).read_text(encoding="utf-8"))
            return app.store.add("palettes", app.user["_id"], item)
        app.run_task(operation, lambda _: (app.toast("Palette imported"), app.navigate("Saved Collections")))


def image_extractor(app, parent):
    heading(parent, "Image color extractor", "Open a picture, sample a pixel, or find its dominant colors.")
    controls = row(parent)
    count = ctk.CTkOptionMenu(controls, values=["3", "5", "8", "10"], fg_color=ELEV, width=80)
    count.set("5")
    count.pack(side="left", padx=5)
    path_label = label(controls, "No image selected", 13, MUTED)
    path_label.pack(side="left", padx=12)
    preview_box = card(parent)
    preview_box.pack(fill="x", padx=5, pady=12)
    preview_label = label(preview_box, "Choose an image to begin", 15, MUTED)
    preview_label.pack(pady=60)
    extracted = []
    results = row(parent)
    def show(result):
        nonlocal extracted
        if not preview_box.winfo_exists(): return
        extracted, image = result
        preview_label.configure(text="")
        image.thumbnail((700, 420))
        preview_label._sample_image = image.copy()
        preview_label._photo = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        preview_label.configure(image=preview_label._photo)
        path_label.configure(text=Path(selected[0]).name)
        for child in results.winfo_children(): child.destroy()
        for item in extracted:
            color = item["hex"]
            tile = card(results); tile.pack(side="left", fill="x", expand=True, padx=3)
            swatch(tile, color, 85, 75).pack(fill="x", padx=5, pady=5)
            label(tile, f"{color} · {item['percent']}%", 12, TEXT).pack(pady=3)
            button(tile, "Copy", lambda c=color: app.copy(c), color=ELEV, width=70).pack(pady=2)
            button(tile, "Favorite", lambda c=color: save_color_dialog(app, c, True), color=ELEV, width=70).pack(pady=(0, 5))
        app.toast("Image colors extracted")
    selected = [""]
    def open_image():
        path = filedialog.askopenfilename(parent=app, filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if path:
            selected[0] = path
            path_label.configure(text="Analyzing image…")
            app.run_task(lambda: extract_colors(path, int(count.get())), show)
    button(controls, "Open image…", open_image).pack(side="left", padx=5)
    button(controls, "Extract again", lambda: app.run_task(lambda: extract_colors(selected[0], int(count.get())), show) if selected[0] else app.toast("Choose an image first"), color=ELEV).pack(side="left", padx=5)
    def save():
        if not extracted: return app.toast("Extract colors first")
        name = prompt(app, "Name extracted palette", Path(selected[0]).stem)
        if name:
            app.run_task(lambda: app.store.add("palettes", app.user["_id"], {"name": name, "colors": [x["hex"] for x in extracted], "harmony_type": "Image extraction", "source_image": Path(selected[0]).name, "is_favorite": False}), lambda _: app.toast("Extracted palette saved"))
    button(parent, "Save extracted palette", save).pack(anchor="w", padx=5, pady=4)
    button(parent, "Export palette…", lambda: export_current(app, Path(selected[0]).stem if selected[0] else "Image palette", [x["hex"] for x in extracted]), color=ELEV).pack(anchor="w", padx=5, pady=4)
    def sample(event):
        if not selected[0] or not getattr(preview_label, "_photo", None): return
        try:
            image = preview_label._sample_image
            x = int(event.x * image.width / max(1, preview_label.winfo_width()))
            y = int(event.y * image.height / max(1, preview_label.winfo_height()))
            color = rgb_to_hex(image.convert("RGB").getpixel((min(image.width-1,x), min(image.height-1,y))))
            commit_color(app, color, "image pixel")
            app.copy(color)
        except Exception as exc: app.show_error(exc)
    preview_label.bind("<Button-1>", sample)


def gradients(app, parent):
    heading(parent, "Gradient studio", "Compose a two-stop gradient and export the exact preview.")
    controls = row(parent)
    kind = ctk.CTkOptionMenu(controls, values=["Linear", "Radial"], fg_color=ELEV)
    editing = app.editing_gradient
    kind.set(editing.get("type","Linear") if editing else "Linear"); kind.pack(side="left", padx=5)
    angle = ctk.CTkSlider(controls, from_=0, to=360, width=230, progress_color=ACCENT)
    angle.set(editing.get("angle",90) if editing else 90); angle.pack(side="left", padx=15)
    angle_label = label(controls, "90°", 13, MUTED); angle_label.pack(side="left")
    stops = [dict(x) for x in editing["color_stops"]] if editing else [{"color": app.current_color, "position": 0}, {"color": "#06B6D4", "position": 100}]
    preview = label(parent, "", 14, TEXT)
    preview.pack(fill="x", padx=5, pady=12)
    stop_frame = row(parent)
    css = ctk.CTkTextbox(parent, height=80, fg_color=PANEL, font=("Consolas", 13))
    css.pack(fill="x", padx=5, pady=10)
    render_token = {"value": 0}
    preview_job = {"id": None}
    def css_code():
        values = ", ".join(f"{s['color']} {s['position']}%" for s in sorted(stops, key=lambda x:x["position"]))
        return f"{kind.get().lower()}-gradient({str(round(angle.get())) + 'deg, ' if kind.get() == 'Linear' else 'circle, '}{values})"
    def update_preview():
        angle_label.configure(text=f"{round(angle.get())}°")
        css.delete("1.0", "end"); css.insert("1.0", css_code())
        render_token["value"] += 1
        token = render_token["value"]
        snapshot = [dict(x) for x in stops]
        chosen_kind, chosen_angle = kind.get(), angle.get()
        if preview_job["id"] is not None:
            app.after_cancel(preview_job["id"])
        preview_job["id"] = app.after(140, lambda: app.run_task(
            lambda: gradient_image(760, 230, snapshot, chosen_kind, chosen_angle),
            lambda image: display(image, token)))
    def display(image, token):
        if token != render_token["value"] or not preview.winfo_exists(): return
        preview._photo = ctk.CTkImage(light_image=image, dark_image=image, size=(760,230))
        preview.configure(image=preview._photo)
    def draw_stops():
        for child in stop_frame.winfo_children(): child.destroy()
        for i, stop in enumerate(stops):
            tile = card(stop_frame); tile.pack(side="left", padx=5)
            swatch(tile, stop["color"], 100, 50).pack(padx=8, pady=8)
            button(tile, stop["color"], lambda index=i: choose_stop(index), color=ELEV, width=110).pack(pady=3)
            slider = ctk.CTkSlider(tile, from_=0, to=100, width=125, command=lambda value, index=i: move_stop(index, value))
            slider.set(stop["position"]); slider.pack(padx=5, pady=5)
            button(tile, "Remove", lambda index=i: remove_stop(index), color=ELEV, width=95).pack(pady=(0, 6))
    def choose_stop(i):
        chosen = colorchooser.askcolor(color=stops[i]["color"], parent=app)[1]
        if chosen: stops[i]["color"] = normalize_hex(chosen); draw_stops(); update_preview()
    def move_stop(i, value):
        stops[i]["position"] = round(value); update_preview()
    def remove_stop(i):
        if len(stops) <= 2: return app.toast("A gradient needs two stops")
        stops.pop(i); draw_stops(); update_preview()
    kind.configure(command=lambda _: update_preview())
    angle.configure(command=lambda _: update_preview())
    buttons = row(parent)
    button(buttons, "Add stop", lambda: (stops.append({"color": app.current_color, "position": 50}), draw_stops(), update_preview()), color=ELEV).pack(side="left", padx=5)
    button(buttons, "Copy CSS", lambda: app.copy(css_code()), color=ELEV).pack(side="left", padx=5)
    def save():
        title = prompt(app, "Name gradient", editing["name"] if editing else "Untitled gradient")
        if title:
            fields = {"name": title, "type": kind.get(), "angle": round(angle.get()), "color_stops": [dict(x) for x in stops]}
            if app.editing_gradient:
                app.run_task(lambda: app.store.update("gradients", app.user["_id"], app.editing_gradient["_id"], fields),lambda _:app.toast("Gradient updated"))
            else:
                app.run_task(lambda: app.store.add("gradients", app.user["_id"], fields),lambda _:app.toast("Gradient saved"))
    button(buttons, "Save gradient", save).pack(side="left", padx=5)
    def from_saved_palette():
        window = ctk.CTkToplevel(app)
        window.title("Choose saved palette")
        window.geometry("360x400")
        window.configure(fg_color=BG)
        label(window,"Choose a palette",20,TEXT,"bold").pack(padx=18,pady=18)
        list_frame = ctk.CTkScrollableFrame(window,fg_color=BG)
        list_frame.pack(fill="both",expand=True,padx=12,pady=5)
        def show(items):
            if not window.winfo_exists():return
            if not items: label(list_frame,"No saved palettes yet.",14,MUTED).pack(pady=20)
            for item in items:
                def select(palette=item):
                    colors = palette["colors"]
                    stops[:] = [{"color":color,"position":round(i*100/(len(colors)-1))} for i,color in enumerate(colors)]
                    window.destroy();draw_stops();update_preview()
                button(list_frame,item["name"],select,color=ELEV).pack(fill="x",pady=4)
        app.run_task(lambda:app.store.list("palettes",app.user["_id"]),show)
    button(buttons,"From saved palette",from_saved_palette,color=ELEV).pack(side="left",padx=5)
    if editing:
        button(buttons,"New gradient",lambda:(setattr(app,"editing_gradient",None),app.navigate("Gradient Studio")),color=ELEV).pack(side="left",padx=5)
    def export():
        path = filedialog.asksaveasfilename(parent=app, defaultextension=".png", filetypes=[("PNG image", "*.png")])
        if path:
            snapshot = [dict(x) for x in stops]
            chosen_kind, chosen_angle = kind.get(), angle.get()
            app.run_task(lambda: gradient_image(1200, 500, snapshot, chosen_kind, chosen_angle).save(path), lambda _: app.toast("Gradient PNG exported"))
    button(buttons, "Export PNG…", export, color=ELEV).pack(side="left", padx=5)
    draw_stops(); update_preview()


def contrast_page(app, parent):
    heading(parent, "Contrast checker", "Check text legibility against WCAG contrast thresholds.")
    controls = row(parent)
    entries = {}
    for name, default in (("Foreground", "#FFFFFF"), ("Background", app.current_color)):
        group = card(controls); group.pack(side="left", padx=5, pady=5)
        label(group, name, 13, MUTED).pack(anchor="w", padx=14, pady=(12, 4))
        line = row(group)
        entry = ctk.CTkEntry(line, width=120, fg_color=ELEV); entry.insert(0, default); entry.pack(side="left", padx=10)
        entries[name] = entry
        button(line, "Choose…", lambda n=name: choose(n), color=ELEV, width=80).pack(side="left", padx=(0,10))
    preview = card(parent); preview.pack(fill="x", padx=5, pady=15)
    sample = label(preview, "The quick brown fox jumps over the lazy dog.", 24, TEXT, "bold")
    sample.pack(padx=22, pady=35)
    comparison = label(parent,"",14,MUTED)
    comparison.pack(anchor="w",padx=8,pady=5)
    ratio = label(parent, "", 29, TEXT, "bold"); ratio.pack(anchor="w", padx=8)
    results = ctk.CTkFrame(parent, fg_color="transparent"); results.pack(anchor="w", padx=8)
    def update():
        try:
            fg, bg = [normalize_hex(entries[x].get()) for x in ("Foreground", "Background")]
            score = contrast(fg, bg)
            differences = tuple(abs(a-b) for a,b in zip(hex_to_rgb(fg),hex_to_rgb(bg)))
            comparison.configure(text=f"RGB difference: R {differences[0]} · G {differences[1]} · B {differences[2]}")
            preview.configure(fg_color=bg); sample.configure(text_color=fg)
            ratio.configure(text=f"{score:.2f}:1 contrast")
            for child in results.winfo_children(): child.destroy()
            for text, threshold in (("AA normal", 4.5), ("AA large", 3), ("AAA normal", 7), ("AAA large", 4.5)):
                label(results, f"{text}: {'PASS' if score >= threshold else 'FAIL'}", 15, "#22C55E" if score >= threshold else ERROR).pack(anchor="w", pady=3)
        except ValueError as exc: app.show_error(exc)
    def choose(name):
        selected = colorchooser.askcolor(color=entries[name].get(), parent=app)[1]
        if selected: entries[name].delete(0,"end"); entries[name].insert(0, normalize_hex(selected)); update()
    button(parent, "Update contrast", update).pack(anchor="w", padx=8, pady=5)
    def suggest():
        bg = normalize_hex(entries["Background"].get())
        candidate = max(("#000000", "#FFFFFF"), key=lambda c: contrast(c,bg))
        entries["Foreground"].delete(0,"end"); entries["Foreground"].insert(0,candidate); update()
    button(parent, "Suggest accessible text", suggest, color=ELEV).pack(anchor="w", padx=8, pady=5)
    update()


def collections(app, parent):
    heading(parent, "Saved collections", "Find and manage your colors, palettes, and gradients.")
    tabs = ctk.CTkTabview(parent, fg_color=BG, segmented_button_selected_color=ACCENT)
    tabs.pack(fill="both", expand=True, padx=4)
    for name in ("Colors", "Palettes", "Gradients"):
        tabs.add(name)
    color_tab = tabs.tab("Colors")
    filters = row(color_tab)
    search = ctk.CTkEntry(filters, placeholder_text="Search name, tag, or HEX", width=260, fg_color=ELEV)
    search.pack(side="left", padx=5)
    favorite_only = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(filters, text="Favorites", variable=favorite_only, fg_color=ACCENT).pack(side="left", padx=8)
    sort = ctk.CTkOptionMenu(filters, values=["Recent", "Oldest", "Name"], fg_color=ELEV)
    sort.pack(side="left", padx=8)
    color_grid = ctk.CTkFrame(color_tab, fg_color="transparent"); color_grid.pack(fill="x")
    data = {"colors": []}
    def color_edit(item):
        new_name = prompt(app, "Edit color name", item["name"])
        if new_name is None: return
        tags = prompt(app, "Comma-separated tags", ", ".join(item.get("tags", [])))
        if tags is None: return
        description = prompt(app, "Description", item.get("description", ""))
        if description is None: return
        collection_name = prompt(app, "Collection name", item.get("collection_name", ""))
        if collection_name is None: return
        chosen = colorchooser.askcolor(color=item["hex"], parent=app)[1]
        if chosen is None: return
        color = normalize_hex(chosen)
        app.run_task(lambda: app.store.update("saved_colors", app.user["_id"], item["_id"], {"name": new_name.strip() or item["name"], "hex":color,"rgb":list(hex_to_rgb(color)), "tags": [x.strip() for x in tags.split(",") if x.strip()], "description": description, "collection_name": collection_name}), lambda _: refresh())
    def refresh(*_):
        def show(items):
            if not color_grid.winfo_exists(): return
            data["colors"] = items
            for child in color_grid.winfo_children(): child.destroy()
            needle = search.get().casefold().strip()
            shown = [x for x in items if (not favorite_only.get() or x.get("is_favorite")) and (needle in (x.get("name", "") + " " + x["hex"] + " " + " ".join(x.get("tags", []))).casefold())]
            if sort.get() == "Name": shown.sort(key=lambda x:x["name"].casefold())
            if sort.get() == "Oldest": shown.reverse()
            if not shown: label(color_grid, "No saved colors match these filters.", 14, MUTED).pack(pady=20)
            for start in range(0, len(shown), 4):
                line = row(color_grid)
                for item in shown[start:start+4]:
                    tile = card(line); tile.pack(side="left", padx=4, pady=4, fill="x", expand=True)
                    swatch(tile, item["hex"], 170, 80).pack(fill="x", padx=8, pady=8)
                    label(tile, item["name"], 14, TEXT, "bold").pack(anchor="w", padx=9)
                    label(tile, item["hex"], 12, MUTED).pack(anchor="w", padx=9)
                    ctl = row(tile)
                    button(ctl, "Copy", lambda c=item["hex"]: app.copy(c), color=ELEV, width=55).pack(side="left", padx=2)
                    button(ctl, "Edit", lambda x=item: color_edit(x), color=ELEV, width=48).pack(side="left", padx=2)
                    button(ctl, "Unfav" if item.get("is_favorite") else "Fav", lambda x=item: toggle_favorite(x), color=ELEV, width=48).pack(side="left", padx=2)
                    button(ctl, "Delete", lambda x=item: delete_item("saved_colors",x,refresh), color=ELEV, width=52).pack(side="left", padx=2)
        app.run_task(lambda: app.store.list("saved_colors", app.user["_id"]), show)
    def toggle_favorite(item):
        app.run_task(lambda: app.store.update("saved_colors", app.user["_id"], item["_id"], {"is_favorite": not item.get("is_favorite",False)}), lambda _: refresh())
    def delete_item(collection, item, reload):
        if messagebox.askyesno("Delete item", f"Delete {item.get('name', 'this item')}?", parent=app):
            app.run_task(lambda: app.store.delete(collection, app.user["_id"], item["_id"]), lambda _: (app.toast("Item deleted"), reload()))
    button(filters, "Search", refresh, color=ELEV).pack(side="left", padx=5)
    refresh()
    palette_tab = tabs.tab("Palettes")
    palette_list = ctk.CTkFrame(palette_tab, fg_color="transparent"); palette_list.pack(fill="x")
    def load_palettes():
        def show(items):
            if not palette_list.winfo_exists(): return
            for child in palette_list.winfo_children(): child.destroy()
            if not items: label(palette_list, "Saved palettes will appear here.", 14, MUTED).pack(pady=20)
            for item in items:
                tile = card(palette_list); tile.pack(fill="x", pady=5)
                label(tile, item["name"], 17, TEXT, "bold").pack(anchor="w", padx=15, pady=(10, 5))
                strip = row(tile)
                for color in item["colors"]:
                    button(strip, color, lambda c=color: app.copy(c), color=color, width=100).pack(side="left", padx=3)
                ctl = row(tile)
                button(ctl, "Export…", lambda x=item: export_current(app,x["name"],x["colors"]), color=ELEV).pack(side="left", padx=5)
                button(ctl, "Rename", lambda x=item: rename_palette(x), color=ELEV).pack(side="left", padx=5)
                button(ctl,"Edit",lambda x=item:(setattr(app,"editing_palette",x),app.navigate("Palette Generator")),color=ELEV).pack(side="left",padx=5)
                button(ctl, "Favorite" if not item.get("is_favorite") else "Unfavorite", lambda x=item: app.run_task(lambda: app.store.update("palettes", app.user["_id"], x["_id"], {"is_favorite": not x.get("is_favorite",False)}), lambda _: load_palettes()), color=ELEV).pack(side="left", padx=5)
                button(ctl, "Delete", lambda x=item: delete_item("palettes",x,load_palettes), color=ELEV).pack(side="left", padx=5)
        app.run_task(lambda: app.store.list("palettes",app.user["_id"]),show)
    def rename_palette(item):
        name = prompt(app,"Rename palette",item["name"])
        if name: app.run_task(lambda: app.store.update("palettes",app.user["_id"],item["_id"],{"name":name}),lambda _:load_palettes())
    load_palettes()
    gradient_tab = tabs.tab("Gradients")
    gradient_list = ctk.CTkFrame(gradient_tab, fg_color="transparent"); gradient_list.pack(fill="x")
    def load_gradients():
        def show(items):
            if not gradient_list.winfo_exists(): return
            for child in gradient_list.winfo_children(): child.destroy()
            if not items: label(gradient_list,"Saved gradients will appear here.",14,MUTED).pack(pady=20)
            for item in items:
                tile = card(gradient_list); tile.pack(fill="x",pady=5)
                label(tile,item["name"],17,TEXT,"bold").pack(anchor="w",padx=15,pady=8)
                label(tile,f"{item['type']} · {item['angle']}° · {len(item['color_stops'])} stops",13,MUTED).pack(anchor="w",padx=15)
                ctl = row(tile)
                button(ctl,"Copy CSS",lambda x=item: app.copy(f"{x['type'].lower()}-gradient({str(x['angle'])+'deg, ' if x['type']=='Linear' else 'circle, '}" + ", ".join(f"{s['color']} {s['position']}%" for s in x["color_stops"]) + ")"),color=ELEV).pack(side="left",padx=5)
                button(ctl,"Edit",lambda x=item:(setattr(app,"editing_gradient",x),app.navigate("Gradient Studio")),color=ELEV).pack(side="left",padx=5)
                button(ctl,"Delete",lambda x=item:delete_item("gradients",x,load_gradients),color=ELEV).pack(side="left",padx=5)
        app.run_task(lambda:app.store.list("gradients",app.user["_id"]),show)
    load_gradients()


def history_page(app, parent):
    heading(parent,"Color history","Return to colors you selected in previous sessions.")
    tools = row(parent)
    search = ctk.CTkEntry(tools,placeholder_text="Search HEX or source",width=240,fg_color=ELEV); search.pack(side="left",padx=5)
    listing = ctk.CTkFrame(parent,fg_color="transparent"); listing.pack(fill="x")
    def refresh():
        def show(items):
            if not listing.winfo_exists(): return
            for child in listing.winfo_children(): child.destroy()
            needle = search.get().casefold().strip()
            shown = [x for x in items if needle in (x["hex"] + " " + x.get("source","")).casefold()]
            if not shown: label(listing,"No history matches your search.",14,MUTED).pack(pady=20)
            for item in shown:
                line = card(listing); line.pack(fill="x",pady=3)
                swatch(line,item["hex"],60,38).pack(side="left",padx=9,pady=7)
                label(line,item["hex"],14,TEXT,"bold").pack(side="left",padx=5)
                label(line,item.get("source","manual"),12,MUTED).pack(side="left",padx=20)
                label(line,item["selected_at"].astimezone().strftime("%d %b %Y, %H:%M"),12,MUTED).pack(side="left",padx=5)
                button(line,"Reuse",lambda c=item["hex"]:(setattr(app,"current_color",c),app.navigate("Color Picker")),color=ELEV,width=65).pack(side="right",padx=6)
                button(line,"Save",lambda c=item["hex"]:save_color_dialog(app,c),color=ELEV,width=60).pack(side="right",padx=3)
        app.run_task(lambda:app.store.list("color_history",app.user["_id"],100),show)
    button(tools,"Search",refresh,color=ELEV).pack(side="left",padx=5)
    def clear():
        if messagebox.askyesno("Clear history","Remove all your color selection history?",parent=app):
            app.run_task(lambda:app.store.clear_history(app.user["_id"]),lambda _:(app.toast("History cleared"),refresh()))
    button(tools,"Clear history",clear,color=ELEV).pack(side="left",padx=5)
    refresh()


def settings(app, parent):
    heading(parent,"Settings & profile","Manage your account and appearance.")
    profile = card(parent); profile.pack(fill="x",padx=5,pady=8)
    label(profile,"Account",20,TEXT,"bold").pack(anchor="w",padx=20,pady=(18,8))
    label(profile,f"@{app.user['username']}  ·  {app.user['email']}",14,MUTED).pack(anchor="w",padx=20)
    display = ctk.CTkEntry(profile,width=280,fg_color=ELEV);display.insert(0,app.user["full_name"]);display.pack(anchor="w",padx=20,pady=10)
    def update_name():
        name = display.get().strip()
        app.run_task(lambda:app.store.update_profile(app.user["_id"],name),lambda _:(app.user.__setitem__("full_name",name),app.toast("Profile updated")))
    button(profile,"Save display name",update_name).pack(anchor="w",padx=20,pady=(0,20))
    appearance = card(parent);appearance.pack(fill="x",padx=5,pady=8)
    label(appearance,"Appearance",20,TEXT,"bold").pack(anchor="w",padx=20,pady=(18,8))
    theme = ctk.CTkOptionMenu(appearance,values=["dark","light"],fg_color=ACCENT)
    theme.set(app.user.get("preferences",{}).get("theme","dark"));theme.pack(anchor="w",padx=20,pady=6)
    def save_theme():
        chosen = theme.get()
        app.run_task(lambda:app.store.set_theme(app.user["_id"],chosen),lambda _:(app.user.setdefault("preferences",{}).__setitem__("theme",chosen),ctk.set_appearance_mode(chosen),app.toast("Theme saved")))
    button(appearance,"Apply theme",save_theme).pack(anchor="w",padx=20,pady=(4,20))
    security = card(parent);security.pack(fill="x",padx=5,pady=8)
    label(security,"Security",20,TEXT,"bold").pack(anchor="w",padx=20,pady=(18,8))
    old = ctk.CTkEntry(security,width=260,placeholder_text="Current password",show="●",fg_color=ELEV);old.pack(anchor="w",padx=20,pady=5)
    new = ctk.CTkEntry(security,width=260,placeholder_text="New password",show="●",fg_color=ELEV);new.pack(anchor="w",padx=20,pady=5)
    button(security,"Change password",lambda:app.run_task(lambda:app.store.change_password(app.user["_id"],old.get(),new.get()),lambda _:(old.delete(0,"end"),new.delete(0,"end"),app.toast("Password changed")))).pack(anchor="w",padx=20,pady=(10,20))
    danger = card(parent);danger.pack(fill="x",padx=5,pady=8)
    label(danger,"Delete account",20,TEXT,"bold").pack(anchor="w",padx=20,pady=(18,8))
    label(danger,"This permanently removes your saved colors, palettes, gradients and history.",13,MUTED).pack(anchor="w",padx=20)
    def delete_account():
        if not messagebox.askyesno("Delete account","Permanently delete your account and all its data?",parent=app):return
        typed = prompt(app,"Type DELETE to confirm")
        if typed == "DELETE":app.run_task(lambda:app.store.delete_account(app.user["_id"]),lambda _:(app.logout(),app.toast("Account deleted")))
    button(danger,"Delete my account",delete_account,color=ERROR).pack(anchor="w",padx=20,pady=20)
