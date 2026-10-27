# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

## Stack

Python 3.11+, Tkinter, CustomTkinter, local MongoDB through PyMongo, Pillow, bcrypt.

## Users

Students and designers creating, checking, and saving colors on a Windows desktop. This audience is inferred from the supplied academic project brief.

## Product Purpose

ChromaForge is an offline desktop workspace for choosing colors, generating palettes and gradients, extracting colors from images, checking contrast, and keeping a personal library.

## Operating Context

The application starts with `python main.py`, uses graphical controls throughout, and saves each account's data to a local MongoDB installation.

## Capabilities and Constraints

GUI-only flow; authentication and user-owned data; local database `chromaforge_db`; color tools; graphical import and export; no web server or browser interface. The provided brief is the source of these requirements.

## Brand Commitments

Name: ChromaForge. Dark premium desktop interface using the brief's navy, violet, cyan, and slate palette.

## Product Principles

- A color should be easy to inspect, copy, reuse, and save.
- Stored data belongs to exactly one account.
- Errors and recovery happen in the GUI.
- Heavy operations must leave the window responsive.
