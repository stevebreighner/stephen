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
PREVIEW_SIZE = 220
THUMB_SIZES = {
    "portrait": (640, 800),
    "square": (700, 700),
    "landscape": (1000, 667),
}


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def yaml_quote(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def yaml_unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\\\", "\\")


def save_jpeg(src, dst, max_size=None):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        if max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, "white")
            if img.mode == "P":
                img = img.convert("RGBA")
            mask = img.getchannel("A") if "A" in img.mode else None
            background.paste(img, mask=mask)
            img = background
        else:
            img = img.convert("RGB")
        img.save(dst, "JPEG", quality=92, optimize=True)


def save_cropped_jpeg(src, dst, size):
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.5))
        img.save(dst, "JPEG", quality=92, optimize=True)


def suggest_orientation(path):
    with Image.open(path) as img:
        width, height = ImageOps.exif_transpose(img).size
    ratio = width / height
    if ratio > 1.15:
        return "landscape"
    if ratio < 0.9:
        return "portrait"
    return "square"


def parse_artwork_file(path):
    text = path.read_text(encoding="utf-8")
    frontmatter = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            body = parts[2].strip()
            current_parent = None
            for line in parts[1].splitlines():
                if not line.strip():
                    continue
                if line.startswith("  ") and current_parent:
                    key, _, value = line.strip().partition(":")
                    frontmatter.setdefault(current_parent, {})[key.strip()] = yaml_unquote(value)
                    continue
                key, _, value = line.partition(":")
                key = key.strip()
                value = value.strip()
                if value:
                    frontmatter[key] = yaml_unquote(value)
                    current_parent = None
                else:
                    frontmatter[key] = {}
                    current_parent = key

    slug = path.stem
    orientation = frontmatter.get("orientation") or "square"
    return {
        "slug": slug,
        "title": frontmatter.get("title") or slug,
        "date": frontmatter.get("date") or date.today().isoformat(),
        "orientation": orientation if orientation in THUMB_SIZES else "square",
        "thumb": frontmatter.get("thumb", ""),
        "image": frontmatter.get("image", ""),
        "medium": frontmatter.get("medium", ""),
        "size": frontmatter.get("size", ""),
        "year": frontmatter.get("year", str(date.today().year)),
        "price": frontmatter.get("price", ""),
        "status": frontmatter.get("status", "Available"),
        "description": body,
    }


class ArtworkManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Artwork Manager")
        self.geometry("980x650")
        self.minsize(860, 580)

        self.current_slug = None
        self.current_date = None
        self.image_path = None
        self.preview_image = None
        self.auto_slug = True
        self.artworks = []

        self.title_var = tk.StringVar()
        self.slug_var = tk.StringVar()
        self.medium_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.year_var = tk.StringVar(value=str(date.today().year))
        self.price_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Available")
        self.orientation_var = tk.StringVar(value="square")
        self.image_var = tk.StringVar(value="No new image selected")

        self._build_ui()
        self.title_var.trace_add("write", self._sync_slug)
        self.slug_var.trace_add("write", self._slug_edited)
        self.refresh_list()
        self.new_artwork()

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, padding=12)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.rowconfigure(1, weight=1)

        ttk.Label(sidebar, text="Artwork").grid(row=0, column=0, sticky="w")
        self.artwork_list = tk.Listbox(sidebar, width=30, exportselection=False)
        self.artwork_list.grid(row=1, column=0, sticky="ns", pady=8)
        self.artwork_list.bind("<<ListboxSelect>>", self.load_selected_artwork)

        ttk.Button(sidebar, text="New Artwork", command=self.new_artwork).grid(
            row=2, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(sidebar, text="Delete Selected", command=self.delete_artwork).grid(
            row=3, column=0, sticky="ew"
        )

        outer = ttk.Frame(self, padding=18)
        outer.grid(row=0, column=1, sticky="nsew")
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

        orientation_row = len(fields)
        ttk.Label(form, text="Grid Thumb").grid(row=orientation_row, column=0, sticky="w", pady=5)
        orientation = ttk.Frame(form)
        orientation.grid(row=orientation_row, column=1, sticky="ew", pady=5, padx=(10, 0))
        for label, value in [
            ("Portrait", "portrait"),
            ("Square", "square"),
            ("Landscape", "landscape"),
        ]:
            ttk.Radiobutton(
                orientation,
                text=label,
                value=value,
                variable=self.orientation_var,
            ).pack(side="left", padx=(0, 14))

        description_row = orientation_row + 1
        ttk.Label(form, text="Description").grid(row=description_row, column=0, sticky="nw", pady=5)
        self.description = tk.Text(form, height=10, wrap="word")
        self.description.grid(row=description_row, column=1, sticky="nsew", pady=5, padx=(10, 0))
        form.rowconfigure(description_row, weight=1)

        image_panel = ttk.Frame(outer)
        image_panel.grid(row=0, column=1, sticky="nsew")
        image_panel.columnconfigure(0, weight=1)
        image_panel.rowconfigure(1, weight=1)

        ttk.Button(image_panel, text="Choose / Replace Image...", command=self.choose_image).grid(
            row=0, column=0, sticky="ew"
        )
        self.preview = ttk.Label(image_panel, text="Preview", anchor="center")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=12)
        ttk.Label(image_panel, textvariable=self.image_var, wraplength=320).grid(
            row=2, column=0, sticky="ew"
        )

        buttons = ttk.Frame(outer)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        buttons.columnconfigure(0, weight=1)

        ttk.Button(buttons, text="Save Artwork", command=self.save_artwork).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(buttons, text="Quit", command=self.destroy).grid(row=0, column=2)

    def refresh_list(self):
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        self.artworks = []
        for md_file in sorted(CONTENT_DIR.glob("*.md")):
            try:
                self.artworks.append(parse_artwork_file(md_file))
            except OSError:
                continue
        self.artworks.sort(key=lambda item: item["title"].lower())

        self.artwork_list.delete(0, tk.END)
        for item in self.artworks:
            self.artwork_list.insert(tk.END, f"{item['title']} ({item['slug']})")

    def _sync_slug(self, *_):
        if self.auto_slug:
            self.slug_var.set(slugify(self.title_var.get()))

    def _slug_edited(self, *_):
        current = self.slug_var.get()
        expected = slugify(self.title_var.get())
        self.auto_slug = current == expected or not current

    def new_artwork(self):
        self.current_slug = None
        self.current_date = None
        self.image_path = None
        self.preview_image = None
        self.auto_slug = True
        self.title_var.set("")
        self.slug_var.set("")
        self.medium_var.set("")
        self.size_var.set("")
        self.year_var.set(str(date.today().year))
        self.price_var.set("")
        self.status_var.set("Available")
        self.orientation_var.set("square")
        self.image_var.set("No new image selected")
        self.description.delete("1.0", "end")
        self.preview.configure(image="", text="Preview")
        self.artwork_list.selection_clear(0, tk.END)

    def load_selected_artwork(self, *_):
        selection = self.artwork_list.curselection()
        if not selection:
            return
        item = self.artworks[selection[0]]
        self.current_slug = item["slug"]
        self.current_date = item["date"]
        self.image_path = None
        self.preview_image = None
        self.auto_slug = False

        self.title_var.set(item["title"])
        self.slug_var.set(item["slug"])
        self.medium_var.set(item["medium"])
        self.size_var.set(item["size"])
        self.year_var.set(item["year"])
        self.price_var.set(item["price"])
        self.status_var.set(item["status"])
        self.orientation_var.set(item["orientation"])
        self.description.delete("1.0", "end")
        self.description.insert("1.0", item["description"])

        main_image = IMAGE_DIR / item["slug"] / "main.jpg"
        if main_image.exists():
            self.image_var.set(f"Existing image: {main_image.relative_to(ROOT_DIR)}")
            self._load_preview(main_image)
        else:
            self.image_var.set("Existing image not found. Choose a replacement image.")
            self.preview.configure(image="", text="Preview")

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
        try:
            self.orientation_var.set(suggest_orientation(self.image_path))
        except OSError:
            pass
        self._load_preview(self.image_path)

    def _load_preview(self, path):
        try:
            if ImageTk is None:
                self.preview.configure(image="", text="Preview unavailable")
                return

            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img)
                img.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img.copy())
            self.preview.configure(image=self.preview_image, text="")
        except OSError as exc:
            self.preview.configure(image="", text="Preview")
            messagebox.showerror("Image Error", f"Could not open that image:\n{exc}")

    def save_artwork(self):
        title = self.title_var.get().strip()
        slug = slugify(self.slug_var.get().strip() or title)
        old_slug = self.current_slug
        medium = self.medium_var.get().strip()
        size = self.size_var.get().strip()
        year = self.year_var.get().strip() or str(date.today().year)
        price = self.price_var.get().strip()
        status = self.status_var.get().strip() or "Available"
        orientation = self.orientation_var.get()
        description = self.description.get("1.0", "end").strip()
        artwork_date = self.current_date or date.today().isoformat()

        if not title:
            messagebox.showerror("Missing Title", "Please enter a title.")
            return
        if not slug:
            messagebox.showerror("Missing Slug", "Please enter a slug or a title.")
            return
        if orientation not in THUMB_SIZES:
            messagebox.showerror("Missing Thumbnail Size", "Please choose portrait, square, or landscape.")
            return

        md_file = CONTENT_DIR / f"{slug}.md"
        old_md_file = CONTENT_DIR / f"{old_slug}.md" if old_slug else None
        art_dir = IMAGE_DIR / slug
        old_art_dir = IMAGE_DIR / old_slug if old_slug else None
        main_image = art_dir / "main.jpg"
        selected_thumb = art_dir / f"thumb-{orientation}.jpg"

        is_rename = old_slug and old_slug != slug
        existing_other = md_file.exists() and md_file != old_md_file
        if existing_other:
            overwrite = messagebox.askyesno(
                "Overwrite Artwork?",
                f"Artwork for '{slug}' already exists. Overwrite it?",
            )
            if not overwrite:
                return

        if not self.image_path and not (old_art_dir and (old_art_dir / "main.jpg").exists()):
            messagebox.showerror("Missing Image", "Please choose an artwork image.")
            return

        try:
            CONTENT_DIR.mkdir(parents=True, exist_ok=True)
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)

            if is_rename:
                if md_file.exists():
                    md_file.unlink()
                if art_dir.exists():
                    shutil.rmtree(art_dir)
                if old_art_dir and old_art_dir.exists():
                    old_art_dir.rename(art_dir)
                if old_md_file and old_md_file.exists():
                    old_md_file.unlink()

            art_dir.mkdir(parents=True, exist_ok=True)

            if self.image_path:
                save_jpeg(self.image_path, main_image)
            elif not main_image.exists() and old_art_dir:
                save_jpeg(old_art_dir / "main.jpg", main_image)

            for thumb_type, thumb_size in THUMB_SIZES.items():
                save_cropped_jpeg(main_image, art_dir / f"thumb-{thumb_type}.jpg", thumb_size)
            shutil.copy2(selected_thumb, art_dir / "thumb.jpg")

            md_file.write_text(
                "\n".join(
                    [
                        "---",
                        f"title: {yaml_quote(title)}",
                        f"date: {artwork_date}",
                        f"orientation: {yaml_quote(orientation)}",
                        f'thumb: "/images/artwork/{slug}/thumb-{orientation}.jpg"',
                        "thumbs:",
                        f'  portrait: "/images/artwork/{slug}/thumb-portrait.jpg"',
                        f'  square: "/images/artwork/{slug}/thumb-square.jpg"',
                        f'  landscape: "/images/artwork/{slug}/thumb-landscape.jpg"',
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
            messagebox.showerror("Save Failed", f"Artwork could not be saved:\n{exc}")
            return

        self.current_slug = slug
        self.current_date = artwork_date
        self.image_path = None
        self.image_var.set(f"Existing image: {main_image.relative_to(ROOT_DIR)}")
        self.refresh_list()
        self.select_slug(slug)
        messagebox.showinfo(
            "Artwork Saved",
            "Artwork saved successfully.\n\n"
            f"{md_file.relative_to(ROOT_DIR)}\n"
            f"{main_image.relative_to(ROOT_DIR)}\n"
            f"{selected_thumb.relative_to(ROOT_DIR)}",
        )

    def select_slug(self, slug):
        for index, item in enumerate(self.artworks):
            if item["slug"] == slug:
                self.artwork_list.selection_clear(0, tk.END)
                self.artwork_list.selection_set(index)
                self.artwork_list.see(index)
                return

    def delete_artwork(self):
        slug = self.current_slug
        if not slug:
            selection = self.artwork_list.curselection()
            if selection:
                slug = self.artworks[selection[0]]["slug"]
        if not slug:
            messagebox.showerror("No Artwork Selected", "Please select artwork to delete.")
            return

        md_file = CONTENT_DIR / f"{slug}.md"
        art_dir = IMAGE_DIR / slug
        confirm = messagebox.askyesno(
            "Delete Artwork?",
            f"Delete '{slug}'?\n\nThis removes the Markdown file and image folder.",
        )
        if not confirm:
            return

        try:
            if md_file.exists():
                md_file.unlink()
            if art_dir.exists():
                shutil.rmtree(art_dir)
        except Exception as exc:
            messagebox.showerror("Delete Failed", f"Artwork could not be deleted:\n{exc}")
            return

        self.refresh_list()
        self.new_artwork()
        messagebox.showinfo("Artwork Deleted", f"Deleted '{slug}'.")


if __name__ == "__main__":
    ArtworkManager().mainloop()
