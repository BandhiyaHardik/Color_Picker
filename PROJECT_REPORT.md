# ChromaForge project report

## Abstract

ChromaForge is a Python desktop application for selecting, generating, analyzing, and preserving colors. Its GUI uses Tkinter and CustomTkinter, its image operations use Pillow, and its account data is stored in a local MongoDB database through PyMongo. The project demonstrates object-oriented organization, validation, secure password hashing, asynchronous tasks, color mathematics, and user-specific persistence.

## Functional requirements

Users can register, log in, edit a profile, choose colors by several controls, generate palettes, extract colors from images, compose gradients, check WCAG contrast, save work, search collections, import and export palettes, and review selection history. Every application action is reachable in the desktop GUI.

## Nonfunctional requirements

The program starts from `main.py`; no command prompt input is used after launch. Heavy operations use background workers. The database stays local. Passwords are bcrypt hashes. Queries for personal records include the authenticated user ID. Connection failures use a graphical Retry screen.

## System design

The entry point creates one `ChromaForgeApp`. The UI module owns window state, authentication screens, navigation, notifications, and a worker queue. Page functions own graphical controls but call `Store` for persistence. Color and file modules contain reusable calculations and import/export code. Tk widgets are changed only on the main event loop.

## Database design and ER diagram

```text
users (_id, full_name, username_key, email_key, password_hash, preferences)
  ├── 1 : many saved_colors (user_id, name, hex, rgb, tags, is_favorite)
  ├── 1 : many palettes (user_id, name, colors, harmony_type, is_favorite)
  ├── 1 : many gradients (user_id, name, type, angle, color_stops)
  └── 1 : many color_history (user_id, hex, source, selected_at)
```

`username_key` and `email_key` have unique indexes. User-owned collections are indexed by `user_id`. Referential ownership is enforced in application queries rather than by a MongoDB foreign key.

## User flow

Splash screen → local database check → login/register → dashboard → feature selection through sidebar → save/edit/export → logout. If the database is unavailable, the user sees the connection instructions and can retry from the same window.

## Module explanation

- `main.py`: single executable entry point.
- `ui.py`: desktop shell, session state, authentication forms, event loop task queue.
- `pages.py`: dashboard and all feature interfaces.
- `database.py`: MongoDB connection, indexes, account services, scoped CRUD.
- `color_math.py`: conversions, WCAG ratio, harmonies, gradient rendering.
- `files.py`: image quantization and palette format serialization.

## Viva questions and short answers

1. **Why Tkinter?** It ships with Python and provides native desktop windows and dialogs.
2. **Why CustomTkinter?** It provides consistent modern controls while staying inside Tkinter.
3. **Why MongoDB?** Document records suit palettes and variable-length gradient stops.
4. **Why a local MongoDB instance?** It keeps saved account data on the same computer and works offline.
5. **Why hash passwords?** A database should never contain recoverable plaintext passwords.
6. **Why bcrypt?** It salts passwords and is deliberately costly to slow guessing attacks.
7. **Why unique indexes?** They enforce unique usernames and emails even under simultaneous registration.
8. **What is an ObjectId?** A MongoDB identifier used for users and saved records.
9. **How are records isolated?** Queries, edits, and deletes match both item ID and authenticated user ID.
10. **Why background workers?** Image analysis and database calls could otherwise freeze the GUI.
11. **Why a result queue?** Tk widgets must be updated on the GUI thread.
12. **How is RGB converted to HSV?** Channels are normalized to 0–1 and converted with color-space equations.
13. **How is HSL different from HSV?** HSL uses lightness; HSV uses value, producing different controls.
14. **How is a palette generated?** Hue angles are shifted according to complementary, analogous, triadic, or other harmony rules.
15. **What is image quantization?** It groups many source pixels into a small representative palette.
16. **How is contrast calculated?** WCAG relative luminance is computed for each color, then `(Llighter + .05)/(Ldarker + .05)`.
17. **Why validate HEX and JSON input?** Invalid data should be rejected before it reaches calculations or storage.
18. **How is a gradient rendered?** Each output pixel is mapped to a linear or radial position and interpolated between adjacent stops.
19. **What happens without MongoDB?** The app shows a graphical connection error with Retry.
20. **How can the app be packaged?** PyInstaller can build a Windows GUI executable using `--windowed`.

## Presentation demo

Show startup and registration, then save a picker color. Generate a harmony palette, export it as CSS, open an image to extract dominant colors, create a gradient and export PNG, check a text contrast ratio, and reopen the app to demonstrate persistence. Show a second account to demonstrate record isolation.

## Limits and future work

The program depends on a local MongoDB service. The closest-name list is intentionally small. Undo/redo, color comparison, and analytics could be added as later modules. Screen capture depends on the operating system allowing desktop capture.
