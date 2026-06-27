#!/usr/bin/env python3

import re
import shutil
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from PIL import Image, ImageOps

try:
    from PIL import ImageTk
except ImportError:
    ImageTk = None


ROOT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = ROOT_DIR / "src/content/artwork"
IMAGE_DIR = ROOT_DIR / "public/images/artwork"
THUMB_SIZE = 600
PREVIEW_SIZE = 220


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def yaml_quote(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def save_jpeg(src, dst, max_size=None):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        if max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, "white")
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.getchannel("A") if "A" in img.mode else None)
            img = background
        else:
            img = img.convert("RGB")
        img.save(dst, "JPEG", quality=92, optimize=True)


class ArtworkCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Create Artwork")
        self.geometry("760x620")
        self.minsize(680, 560)

        self.image_path = None
        self.preview_image = None
        self.title_var = tk.StringVar()
        self.slug_var = tk.StringVar()
        self.medium_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.year_var = tk.StringVar(value=str(date.today().year))
        self.price_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Available")
        self.image_var = tk.StringVar(value="No image selected")
        self.auto_slug = True

        self._build_ui()
        self.title_var.trace_add("write", self._sync_slug)
        self.slug_var.trace_add("write", self._slug_edited)

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        outer = ttk.Frame(self, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        form = ttk.Frame(outer)
        form.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        form.columnconfigure(1, weight=1)

        fields = [
            ("Title", self.title_var),
            ("Slug", self.slug_var),
            ("Medium", self.medium_var),
            ("Size", self.size_var),
            ("Year", self.year_var),
            ("Price", self.price_var),
            ("Status", self.status_var),
        ]

        for row, (label, var) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(form, textvariable=var).grid(
                row=row, column=1, sticky="ew", pady=5, padx=(10, 0)
            )

        ttk.Label(form, text="Description").grid(row=len(fields), column=0, sticky="nw", pady=5)
        self.description = tk.Text(form, height=9, wrap="word")
        self.description.grid(
            row=len(fields), column=1, sticky="nsew", pady=5, padx=(10, 0)
        )
        form.rowconfigure(len(fields), weight=1)

        image_panel = ttk.Frame(outer)
        image_panel.grid(row=0, column=1, sticky="nsew")
        image_panel.columnconfigure(0, weight=1)
        image_panel.rowconfigure(1, weight=1)

        ttk.Button(image_panel, text="Choose Image...", command=self.choose_image).grid(
            row=0, column=0, sticky="ew"
        )

        self.preview = ttk.Label(image_panel, text="Preview", anchor="center")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=12)

        image_label = ttk.Label(image_panel, textvariable=self.image_var, wraplength=300)
        image_label.grid(row=2, column=0, sticky="ew")

        buttons = ttk.Frame(outer)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        buttons.columnconfigure(0, weight=1)

        ttk.Button(buttons, text="Create Artwork", command=self.create_artwork).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(buttons, text="Quit", command=self.destroy).grid(row=0, column=2)

    def _sync_slug(self, *_):
        if self.auto_slug:
            self.slug_var.set(slugify(self.title_var.get()))

    def _slug_edited(self, *_):
        current = self.slug_var.get()
        expected = slugify(self.title_var.get())
        self.auto_slug = current == expected or not current

    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Select artwork image",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        self.image_path = Path(path)
        self.image_var.set(str(self.image_path))
        self._load_preview()

    def _load_preview(self):
        try:
            if ImageTk is None:
                self.preview.configure(text="Preview unavailable")
                return

            with Image.open(self.image_path) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img.copy())
            self.preview.configure(image=self.preview_image, text="")
        except OSError as exc:
            self.image_path = None
            self.image_var.set("No image selected")
            self.preview.configure(image="", text="Preview")
            messagebox.showerror("Image Error", f"Could not open that image:\n{exc}")

    def create_artwork(self):
        title = self.title_var.get().strip()
        slug = slugify(self.slug_var.get().strip() or title)
        medium = self.medium_var.get().strip()
        size = self.size_var.get().strip()
        year = self.year_var.get().strip() or str(date.today().year)
        price = self.price_var.get().strip()
        status = self.status_var.get().strip() or "Available"
        description = self.description.get("1.0", "end").strip()

        if not title:
            messagebox.showerror("Missing Title", "Please enter a title.")
            return
        if not slug:
            messagebox.showerror("Missing Slug", "Please enter a slug or a title.")
            return
        if not self.image_path:
            messagebox.showerror("Missing Image", "Please choose an artwork image.")
            return

        md_file = CONTENT_DIR / f"{slug}.md"
        art_dir = IMAGE_DIR / slug
        main_image = art_dir / "main.jpg"
        thumb_image = art_dir / "thumb.jpg"

        if md_file.exists() or art_dir.exists():
            overwrite = messagebox.askyesno(
                "Overwrite Artwork?",
                f"Artwork for '{slug}' already exists. Overwrite it?",
            )
            if not overwrite:
                return

        try:
            CONTENT_DIR.mkdir(parents=True, exist_ok=True)
            if art_dir.exists():
                shutil.rmtree(art_dir)
            art_dir.mkdir(parents=True, exist_ok=True)

            save_jpeg(self.image_path, main_image)
            save_jpeg(main_image, thumb_image, THUMB_SIZE)

            md_file.write_text(
                "\n".join(
                    [
                        "---",
                        f"title: {yaml_quote(title)}",
                        f"date: {date.today().isoformat()}",
                        f'thumb: "/images/artwork/{slug}/thumb.jpg"',
                        f'image: "/images/artwork/{slug}/main.jpg"',
                        f"medium: {yaml_quote(medium)}",
                        f"size: {yaml_quote(size)}",
                        f"year: {yaml_quote(year)}",
                        f"price: {yaml_quote(price)}",
                        f"status: {yaml_quote(status)}",
                        "---",
                        "",
                        description,
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        except Exception as exc:
            messagebox.showerror("Create Failed", f"Artwork could not be created:\n{exc}")
            return

        self.slug_var.set(slug)
        messagebox.showinfo(
            "Artwork Created",
            "Artwork created successfully.\n\n"
            f"{md_file.relative_to(ROOT_DIR)}\n"
            f"{main_image.relative_to(ROOT_DIR)}\n"
            f"{thumb_image.relative_to(ROOT_DIR)}",
        )


if __name__ == "__main__":
    ArtworkCreator().mainloop()
