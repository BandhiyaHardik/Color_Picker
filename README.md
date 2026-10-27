# ChromaForge — Advanced Color Picker & Palette Studio

ChromaForge is a Windows desktop color workspace built with Tkinter, CustomTkinter, Pillow, bcrypt, and local MongoDB. It runs entirely inside a desktop window; it does not start a browser or web server.

## Problem and objectives

Color work often gets split across picker tools, image samplers, palette generators, and notes. ChromaForge brings selection, comparison, saved work, and account-specific history into one offline application. Its objectives are accurate color calculations, quick graphical workflows, and durable local storage.

## Requirements

- Python 3.11 or newer
- MongoDB Community Server running locally on `mongodb://localhost:27017/`
- Windows 10/11 recommended

## Install and run (PowerShell)

```powershell
cd D:\Python_Color_Picker
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks venv activation, use `.\.venv\Scripts\python.exe main.py` and `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` instead. After launch, all interaction stays in the GUI.

Install MongoDB Community Server for Windows from the official MongoDB installer and select the Windows Service option. Start the MongoDB service through **Services** if it is stopped. The application will show a graphical Retry screen until the local server is reachable. It creates `chromaforge_db` and indexes automatically.

## Architecture and modules

```text
main.py                     one GUI entry point
chromaforge/ui.py           window shell, authentication, navigation, async tasks
chromaforge/pages.py        feature pages and dialogs
chromaforge/database.py     PyMongo repository, account and ownership rules
chromaforge/color_math.py   color conversions, harmony, contrast, gradients
chromaforge/files.py        image extraction and palette import/export
tests/                      focused math and validation tests
```

User flow: splash → MongoDB check → login/register → dashboard → sidebar feature pages → logout. Database operations and image analysis run in a worker pool; widgets are updated on Tk's main thread. Passwords use salted bcrypt hashes. Each user-owned MongoDB query uses the authenticated account's ObjectId.

## Database design

Database `chromaforge_db` contains `users`, `saved_colors`, `palettes`, `gradients`, and `color_history`. The `users` collection has unique normalized username and email indexes. Each other collection has a `user_id` ObjectId referencing a user. For an ER diagram, draw **users 1→many saved_colors / palettes / gradients / color_history**.

## Features

- Graphical registration, login, profile editing, password changes, theme preference, and account deletion.
- Dashboard with real MongoDB counts, recent selections and palettes, and favorite colors.
- Color picker with a hue wheel, saturation/value canvas, HEX, RGB, HSV, HSL inputs, presets, screen sampling, named color approximation, CMYK, and copy/save actions.
- Harmony-based palette generation with swatch locking, editing, reordering, saving, and JSON/CSS/SCSS/TXT/GPL/PNG export.
- Image extraction from PNG/JPEG/WebP/BMP, dominant color percentages, click-to-sample, and saved extracted palettes.
- Linear and radial gradients with editable stops, saved palette input, CSS, saved projects, and PNG export.
- WCAG contrast ratio, AA/AAA evaluations, and side-by-side RGB difference information.
- Saved color, palette, and gradient management and editing, favorites, search, history, JSON palette import, and graphical file dialogs.

## Test and package

```powershell
python -m pytest -q
python -m PyInstaller --noconfirm --windowed --onefile --name ChromaForge main.py
```

The executable still needs MongoDB running locally. For reproducible academic demonstration, run from the source venv first.

## Demo walkthrough

1. Start MongoDB and run `python main.py`.
2. Register, log in, and review empty dashboard counts.
3. Enter a HEX color, adjust sliders, save it, and view history.
4. Generate and save a palette, then export CSS or PNG.
5. Open an image, inspect dominant colors, and save the extracted palette.
6. Build a gradient, copy CSS, export PNG, then check contrast.
7. Close and reopen the app; sign in to confirm saved data persists.

## Limitations and future improvements

The desktop version requires a running local MongoDB service. Color naming uses a small local set of common CSS names. The screen picker captures the visible virtual desktop and may be limited by OS display permissions. Undo/redo and visual analytics are future additions. Image analysis ignores fully transparent pixels; partially transparent pixels contribute their stored RGB values.

## Academic project notes

**Abstract:** ChromaForge applies object-oriented Python, desktop GUI design, color mathematics, image processing, authentication, and document-oriented persistence to practical color workflows.

**Functional requirements:** account registration/login; precise color selection; palette, image, gradient and contrast tools; save, search, import, export, and history. **Nonfunctional requirements:** GUI-only interaction, local operation, responsive processing, safe password storage, and account ownership isolation.

**Suggested viva questions:** Why use CustomTkinter? Why use MongoDB locally? Why hash passwords? Why bcrypt? Why unique indexes? What is an ObjectId? How is user ownership enforced? Why run image analysis in a worker? Why must Tk widget updates stay on the main thread? How is HSV different from HSL? How is WCAG contrast computed? Why quantize images? How are transparent pixels handled? How are harmony colors generated? Why validate imported JSON? Why debounce color history? How does PNG gradient rendering work? What happens if MongoDB is unavailable?

**Screenshots:** Capture the splash, login, dashboard, picker, palette generator, image extractor, gradient studio, and collections screens during your local demo. No screenshots are bundled because this workspace has no running MongoDB service or user account.
