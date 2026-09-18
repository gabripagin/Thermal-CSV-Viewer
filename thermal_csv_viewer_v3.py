"""
Thermal Image Viewer
Developed by Gabriel Pagin — 2026.

"""
# Gerar Executável:
# python -m PyInstaller --onefile --windowed --clean --icon=icone.ico --add-data "icone.png;." --add-data "logo.ico;." thermal_csv_viewer_pagin_english_version.py

import os
import sys
import shutil
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle as MplRectangle, Ellipse as MplEllipsePatch
import matplotlib.pyplot as plt
from PIL import Image, ImageTk


def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS

    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


BG_MAIN = "darkgrey"  
BG_PANEL = "lightgrey" 
BTN_COLOR = "gainsboro" 
HIGHLIGHT_COLOR = "#2ECC71"
DELETE_COLOR = "darkred"
BORDA = "#6E7B7D"
area_color = "black"


class ThermalViewer:

    ANNOTATION_FILENAME = "annotation_areas.csv"  # mantido por compatibilidade com versões antigas

    def _annotation_filename_for_folder(self, folder):
        nome_pasta = os.path.basename(os.path.normpath(folder))
        # Sanitiza o nome da pasta para uso seguro em nome de arquivo
        nome_pasta = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in nome_pasta)
        if not nome_pasta:
            nome_pasta = "pasta"
        return f"annotation_areas_{nome_pasta}.csv"
    ANNOTATION_COLUMNS = ["id", "arquivo", "classe", "forma", "x0", "y0", "x1", "y1"]

    def __init__(self, root):
        self.root = root

        try:
            self.root.iconbitmap(
                resource_path("logo.ico")
            )
        except Exception:
            pass

        self.root.title("Thermal CSV Viewer")
        self.root.geometry("800x700")
        self.root.minsize(800, 700)
        self.root.resizable(False, False)
        self.root.configure(bg=BG_MAIN)

        self.csv_files = []
        self.current_index = 0
        self.current_data = None
        self.colorbar = None

        # --- Seleção de imagens para mover ---
        self.selected_files = set()

        # --- Seleção / anotação de áreas ---
        self.area_mode = None            # None | "rect" | "ellipse"
        self.ajustar_mode = False        # modo de redimensionar área já criada
        self._press_xy = None

        # Criação de nova área (retangular/elíptica) com pré-visualização ao vivo
        self._creating = False
        self._create_start = None          # (x, y) em coords de dados, onde o arrasto começou
        self._create_preview_patch = None  # patch temporário mostrado durante o arrasto

        # Ajuste (redimensionamento) de área já existente, via handles visíveis
        self._resizing = False
        self._resize_handle_active = None   # "esquerda" | "direita" | "topo" | "fundo"
        self._resize_center = None          # (cx, cy) fixo durante o arrasto
        self._resize_orig_bounds = None     # (x0, y0, x1, y1) no início do arrasto
        self._resize_live_bounds = None     # bounds atualizados a cada movimento
        self._handle_artists = {}           # nome do handle -> artista desenhado no eixo

        # Mover (arrastar) uma área já existente, clicando dentro dela em modo Ajustar
        self._moving = False
        self._move_start = None         # (x, y) em coords de dados, onde o arrasto começou
        self._move_orig_bounds = None   # (x0, y0, x1, y1) no início do arrasto
        self._move_live_bounds = None   # bounds atualizados a cada movimento

        # Image zoom (mouse scroll) — stores the "home" (whole-image) view so it can be reset
        self._zoom_home_xlim = None
        self._zoom_home_ylim = None

        self.annotation_csv_path = None
        self.annotations = []            # lista de dicts (linhas do annotation_areas.csv)
        self.annotation_patches = {}     # id -> (patch, text_obj, ann) desenhados na imagem atual
        self.selected_annotation_id = None
        self.last_area_pixel_count = None  # nº de pixels da última área selecionada (barra de status)

        self.classes = []                # nomes de classes definidas pelo usuário

        self.build_gui()

    def build_gui(self):

        top = tk.Frame(self.root, bg=BG_MAIN)
        top.pack(fill="x", pady=5)

        # Caminho do logo
        logo_path = "icone.png"

        try:

            logo_img = Image.open(resource_path(logo_path))
            logo_img = logo_img.resize((40, 40))

            self.logo_tk = ImageTk.PhotoImage(logo_img)

            self.logo = tk.Label(
                top,
                image=self.logo_tk,
                bg=BG_MAIN
            )

        except Exception:

            self.logo = tk.Label(
                top,
                text="LOGO",
                bg="black",
                width=15
            )

        self.logo.pack(side="left", padx=10)

        title = tk.Label(
            top,
            text="          Thermographic Image Viewer                    ",
            font=("Arial", 15, "bold"),
            bg=BG_MAIN,
            fg="black"
        )
        title.pack(side="left", padx=20)

        copyright_label = tk.Label(
            top,
            text="© Gabriel Pagin 2026",
            bg=BG_MAIN,
            fg="gray",
            font=("Segoe UI", 7)
        )
        copyright_label.pack(side="left", padx=25)
        
        self.help_btn = tk.Button(
            top,
            text="?",
            bg="moccasin",
            fg="black",
            font=("Arial", 10, "bold"),
            width=2,
            command=self.show_shortcuts_help
        )
        self.help_btn.pack(side="left", padx=0)

        main = tk.Frame(self.root, bg=BG_MAIN)
        main.pack(fill="both", expand=True, pady=12, padx=15)

        left = tk.Frame(
            main,
            bg=BG_MAIN
        )

        left.pack(
            side="left",
            fill="both",
            expand=False
        )

        self.filename_label = tk.Label(
            left,
            text="No file uploaded",
            bg=BG_MAIN,
            fg="Black",
            font=("Arial", 12)
        )
        self.filename_label.pack()

        self.fig = Figure(figsize=(5, 4), facecolor="lightgray")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("whitesmoke")

        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(100, 0)

        self.ax.grid(True, alpha=0.3)

        self.ax.text(
            50,
            50,
            "No folder loaded",
            ha="center",
            va="center",
            fontsize=14,
            color="black"
        )

        self.ax.set_xticks([])
        self.ax.set_yticks([])


        self.hline = self.ax.axhline(
            color='white',
            lw=0.5
        )

        self.vline = self.ax.axvline(
            color='white',
            lw=0.5
        )

        self.temp_text = self.ax.text(
            0,
            0,
            "",
            color="white",
            fontsize=10,
            bbox=dict(
                facecolor="black",
                alpha=0.7
            )
        )

        image_frame = tk.Frame(
            left,
            bg=BORDA,
            bd=8,
            relief="ridge"
        )

        image_frame.pack(
            fill="none",
            expand=False,
            padx=10,
            pady=10
        )

        self.canvas = FigureCanvasTkAgg(
            self.fig,
            master=image_frame
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            padx=3,
            pady=3
        )

        self.canvas.mpl_connect("motion_notify_event", self.mouse_move)
        self.canvas.mpl_connect("scroll_event", self.zoom)
        self.canvas.mpl_connect("button_press_event", self.on_canvas_press)
        self.canvas.mpl_connect("button_release_event", self.on_canvas_release)

        self._update_canvas_cursor()

        # Atalhos de teclado globais
        self.root.bind("<Key>", self.on_key_press)

        nav = tk.Frame(left, bg=BG_MAIN)
        nav.pack(pady=5)

        tk.Button(nav, text="⬅ Previous", bg=BTN_COLOR, width=10, height=2, font=5,
                  command=self.previous_image).pack(side="left", padx=5)

        tk.Button(nav, text="Next ➡", bg=BTN_COLOR, width=10, height=2, font=5,
                  command=self.next_image).pack(side="left", padx=5)

        self.select_btn = tk.Button(
            nav,
            text="Select",
            bg=BTN_COLOR,
            width=12,
            height=2,
            font=5,
            command=self.toggle_select_current
        )
        self.select_btn.pack(side="left", padx=5)

        move_frame = tk.Frame(left, bg=BG_MAIN)
        move_frame.pack(fill="x", pady=5)

        self.selected_label = tk.Label(
            move_frame,
            text="Selected images: 0",
            bg=BG_MAIN,
            fg="black"
        )
        self.selected_label.pack(side="left", padx=5)


        self.move_btn = tk.Button(
            nav,
            text="Move",
            bg=BTN_COLOR,
            width=10,
            height=2,
            font=5,
            state="disabled",
            command=self.move_selected_images
        )
        self.move_btn.pack(side="left", padx=5)
        
        self.status = tk.Label(
            left,
            text="X=- Y=- Temperature=-",
            bg="gray",
            fg="white",
            anchor="w",
            font=("Arial", 9, "bold")
        )
        self.status.pack(fill="x")

        right = tk.Frame(
            main,
            width=200,
            bg=BG_MAIN
        )

        right.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10
        )

        right.pack_propagate(False)

        pasta_frame = tk.Frame(right, bg=BG_MAIN)
        pasta_frame.pack(fill="x", pady=5)

        tk.Button(
            pasta_frame,
            text="Select folder",
            bg=BTN_COLOR,
            command=self.select_folder
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            pasta_frame,
            text="Skip to image",
            bg=BTN_COLOR,
            command=self.jump_to_file
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.min_label = tk.Label(right, text="Min:", bg=BG_MAIN, fg="black")
        self.min_label.pack(anchor="w")

        self.max_label = tk.Label(right, text="Max:", bg=BG_MAIN, fg="black")
        self.max_label.pack(anchor="w")

        self.mean_label = tk.Label(right, text="Mean:", bg=BG_MAIN, fg="black")
        self.mean_label.pack(anchor="w")

        self.std_label = tk.Label(right, text="Standard deviation:", bg=BG_MAIN, fg="black")
        self.std_label.pack(anchor="w")

        tk.Label(right, text="Minimum scale", bg=BG_MAIN, fg="black").pack(anchor="w")
        self.vmin_entry = tk.Entry(right)
        self.vmin_entry.pack(fill="x")

        tk.Label(right, text="Maximum scale", bg=BG_MAIN, fg="black").pack(anchor="w")
        self.vmax_entry = tk.Entry(right)
        self.vmax_entry.pack(fill="x")

        tk.Button(right, text="Apply Scale", bg=BTN_COLOR,
                  command=self.show_image).pack(fill="x", pady=5)

        tk.Label(right, text="Color palette", bg=BG_MAIN, fg="black").pack(anchor="w")

        self.cmap = ttk.Combobox(
            right,
            state="readonly",
            values=["turbo", "inferno", "magma", "plasma", "viridis", "jet", "hot", "coolwarm", "gray", "gray_r"]
        )
        self.cmap.set("turbo")
        self.cmap.pack(fill="x")
        self.cmap.bind("<<ComboboxSelected>>", lambda e: self.show_image())

        # --- Classes de anotação ---
        tk.Button(
            right,
            text="Add Labels",
            bg=BTN_COLOR,
            command=self.open_class_manager
        ).pack(fill="x", pady=(10, 2))

        # --- Seleção de área ---
        tk.Label(
            right,
            text="Select Area",
            bg=BG_MAIN,
            fg="black",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(8, 2))

        area_shape_frame = tk.Frame(right, bg=BG_MAIN)
        area_shape_frame.pack(fill="x", pady=2)

        self.rect_mode_btn = tk.Button(
            area_shape_frame,
            text="Rectangular",
            bg=BTN_COLOR,
            command=lambda: self.set_area_mode("rect")
        )
        self.rect_mode_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.ellipse_mode_btn = tk.Button(
            area_shape_frame,
            text="Circle",
            bg=BTN_COLOR,
            command=lambda: self.set_area_mode("ellipse")
        )
        self.ellipse_mode_btn.pack(side="left", fill="x", expand=True, padx=(2, 0))

        self.ajustar_btn = tk.Button(
            right,
            text="Adjust size",
            bg=BTN_COLOR,
            command=self.toggle_ajustar_mode
        )
        self.ajustar_btn.pack(fill="x", pady=(4, 2))

        area_fixa_frame = tk.Frame(right, bg=BG_MAIN)
        area_fixa_frame.pack(fill="x", pady=(4, 0))

        self.area_fixa_var = tk.BooleanVar(value=False)

        self.area_fixa_check = tk.Checkbutton(
            area_fixa_frame,
            text="Fixed area",
            variable=self.area_fixa_var,
            bg=BG_MAIN,
            fg="black",
            activebackground=BG_MAIN,
            activeforeground="black",
            selectcolor=BG_MAIN
        )
        self.area_fixa_check.pack(side="left")

        area_fixa_dims_frame = tk.Frame(right, bg=BG_MAIN)
        area_fixa_dims_frame.pack(fill="x", pady=(0, 4))

        tk.Label(area_fixa_dims_frame, text="Width:", bg=BG_MAIN, fg="black").pack(side="left")
        self.largura_fixa_entry = tk.Entry(area_fixa_dims_frame, width=5)
        self.largura_fixa_entry.insert(0, "20")
        self.largura_fixa_entry.pack(side="left", padx=(2, 8))
        self.largura_fixa_entry.bind("<Return>", self.apply_fixed_size_to_selected)
        self.largura_fixa_entry.bind("<FocusOut>", self.apply_fixed_size_to_selected)

        tk.Label(area_fixa_dims_frame, text="Height:", bg=BG_MAIN, fg="black").pack(side="left")
        self.altura_fixa_entry = tk.Entry(area_fixa_dims_frame, width=5)
        self.altura_fixa_entry.insert(0, "20")
        self.altura_fixa_entry.pack(side="left", padx=(2, 0))
        self.altura_fixa_entry.bind("<Return>", self.apply_fixed_size_to_selected)
        self.altura_fixa_entry.bind("<FocusOut>", self.apply_fixed_size_to_selected)

        self.delete_area_btn = tk.Button(
            right,
            text="Delete Area",
            bg=DELETE_COLOR,
            fg="black",
            state="disabled",
            command=self.delete_selected_annotation
        )
        self.delete_area_btn.pack(fill="x", pady=(4, 8))

        hist_png_frame = tk.Frame(right, bg=BG_MAIN)
        hist_png_frame.pack(fill="x", pady=2)

        tk.Button(
            hist_png_frame,
            text="Histogram",
            bg=BTN_COLOR,
            width=7,
            height=1,
            command=self.show_histogram
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            hist_png_frame,
            text="Save PNG",
            bg=BTN_COLOR,
            width=7,
            height=1,
            command=self.save_png
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        invert_frame = tk.Frame(right, bg=BG_MAIN)
        invert_frame.pack(fill="x", pady=2)

        tk.Button(
            invert_frame,
            text="Flip Vertically",
            bg=BTN_COLOR,
            width=7,
            height=1,
            command=self.invert_vertical
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            invert_frame,
            text="Flip Horizontally",
            bg=BTN_COLOR,
            width=7,
            height=1,
            command=self.invert_horizontal
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        color_switch_frame = tk.Frame(right, bg=BG_MAIN)
        color_switch_frame.pack(fill="x", pady=(6, 2))

        tk.Label(color_switch_frame, text="Area Color:", bg=BG_MAIN, fg="black").pack(side="left")

        self.area_color_btn = tk.Button(
            color_switch_frame,
            text="⚫ Black" if area_color == "black" else "⚪ White",
            bg="black" if area_color == "black" else "white",
            fg="white" if area_color == "black" else "black",
            width=10,
            height=1,
            command=self.toggle_area_color
        )
        self.area_color_btn.pack(side="left", padx=(3, 0))

    # ------------------------------------------------------------------
    # Pasta / carregamento de imagens
    # ------------------------------------------------------------------
    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.csv_files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".csv") and not f.lower().startswith("annotation_areas")
        ])

        if not self.csv_files:
            messagebox.showerror("Error", "No CSV found")
            return

        self.load_annotations_for_folder(folder)

        self.current_index = 0
        self.selected_files = set()
        self.selected_annotation_id = None
        self.delete_area_btn.config(state="disabled")
        self.set_area_mode(None)
        self.disable_ajustar_mode()
        self.load_current()

    def show_error_image(self):

        self.fig.clear()

        self.ax = self.fig.add_subplot(111)

        self.ax.set_facecolor("black")

        self.ax.text(
            0.5,
            0.5,
            "IMAGE ERROR",
            color="white",
            fontsize=30,
            ha="center",
            va="center",
            transform=self.ax.transAxes,
            bbox=dict(
                facecolor="black",
                edgecolor="none",
                boxstyle="round,pad=0.5"
            )
        )

        self.ax.axis("off")

        self.annotation_patches = {}
        self._handle_artists = {}
        self.selected_annotation_id = None
        if hasattr(self, "delete_area_btn"):
            self.delete_area_btn.config(state="disabled")

        self.canvas.draw()

    def load_current(self):

        file = self.csv_files[self.current_index]

        self.filename_label.config(
            text=os.path.basename(file)
        )

        self.selected_annotation_id = None
        if hasattr(self, "delete_area_btn"):
            self.delete_area_btn.config(state="disabled")

        self._cancel_area_creation()
        self._cancel_handle_resize()
        self._cancel_move_annotation()
        self._handle_artists = {}  # a imagem/eixo vão mudar; handles antigos somem

        self.update_selection_ui()

        try:

            df = pd.read_csv(
                file,
                header=None,
                on_bad_lines="skip"
            )

            df = df.apply(
                pd.to_numeric,
                errors="coerce"
            )

            df = df.dropna(
                axis=0,
                how="all"
            )

            df = df.dropna(
                axis=1,
                how="all"
            )

            self.current_data = df.values.astype(float)

            if self.current_data.size == 0:
                raise ValueError("Empty image")

            mn = np.nanmin(self.current_data)
            mx = np.nanmax(self.current_data)

            self.min_label.config(
                text=f"Min: {mn:.2f} °C"
            )

            self.max_label.config(
                text=f"Max: {mx:.2f} °C"
            )

            self.mean_label.config(
                text=f"Média: {np.nanmean(self.current_data):.2f} °C"
            )

            self.std_label.config(
                text=f"Desvio: {np.nanstd(self.current_data):.2f}"
            )

            self.show_image()

        except Exception as e:

            print(
                f"Error opening{file}: {e}"
            )

            self.current_data = None

            self.min_label.config(text="Min: -")
            self.max_label.config(text="Max: -")
            self.mean_label.config(text="Mean: -")
            self.std_label.config(text="Standard deviation: -")

            self.show_error_image()

    def show_image(self):
        if self.current_data is None:
            return

        self._handle_artists = {}  # o eixo será recriado; handles antigos não existem mais

        self.fig.clear()

        self.ax = self.fig.add_subplot(111)

        try:
            vmin = float(self.vmin_entry.get())
            vmax = float(self.vmax_entry.get())
        except Exception:
            vmin = np.min(self.current_data)
            vmax = np.max(self.current_data)

        img = self.ax.imshow(
            self.current_data,
            cmap=self.cmap.get(),
            vmin=vmin,
            vmax=vmax,
            interpolation="nearest"
        )

        self.temp_text = self.ax.text(
            0,
            0,
            "",
            color="white",
            fontsize=10,
            bbox=dict(
                facecolor="black",
                alpha=0.7
            )
        )

        self.hline = self.ax.axhline(
            color="white",
            linewidth=0.5
        )

        self.vline = self.ax.axvline(
            color="white",
            linewidth=0.5
        )

        self.ax.axis("off")

        self.colorbar = self.fig.colorbar(img, ax=self.ax)

        self.draw_annotations()

        self.canvas.draw()

        # Store the "home" view (whole image) so zoom can be reset back to it
        self._zoom_home_xlim = self.ax.get_xlim()
        self._zoom_home_ylim = self.ax.get_ylim()

    def mouse_move(self, event):

        if self.current_data is None:
            return

        if event.xdata is None or event.ydata is None:
            return

        if self._resizing:
            self._update_handle_resize_preview(event)

        if self._moving:
            self._update_move_preview(event)

        if self._creating:
            self._update_create_preview(event)

        x = int(event.xdata)
        y = int(event.ydata)

        try:

            temp = self.current_data[y, x]

            texto_status = f"X={x}  Y={y}  Temp={temp:.2f} °C"

            if self.last_area_pixel_count is not None:
                texto_status += f"   |   Pixels of the selected area: {self.last_area_pixel_count}"

            self.status.config(
                text=texto_status
            )

            # Deslocar o rótulo de temperatura 
            self.temp_text.set_position(
                (x + 7, y - 7)
            )

            self.temp_text.set_text(
                f"{temp:.2f}°C"
            )

            self.canvas.draw_idle()
            self.hline.set_ydata([y])
            self.vline.set_xdata([x])

        except Exception as e:
            print(e)

    def _clamp_window(self, new_min, new_max, limit_min, limit_max):
        # Keeps the window [new_min, new_max] fully inside [limit_min, limit_max],
        # shifting it (without resizing) if it goes past either side — this is
        # what makes the image stay "flush" against the edge instead of showing
        # blank space beyond the actual image.
        size = new_max - new_min

        if new_min < limit_min:
            new_min = limit_min
            new_max = new_min + size

        if new_max > limit_max:
            new_max = limit_max
            new_min = new_max - size

        new_min = max(new_min, limit_min)
        new_max = min(new_max, limit_max)

        return new_min, new_max

    def zoom(self, event):
        if event.xdata is None or event.ydata is None:
            return

        if self._zoom_home_xlim is None or self._zoom_home_ylim is None:
            self._zoom_home_xlim = self.ax.get_xlim()
            self._zoom_home_ylim = self.ax.get_ylim()

        scale = 1 / 1.2 if event.button == "up" else 1.2

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        home_x_min, home_x_max = min(self._zoom_home_xlim), max(self._zoom_home_xlim)
        home_y_min, home_y_max = min(self._zoom_home_ylim), max(self._zoom_home_ylim)

        x_min, x_max = min(xlim), max(xlim)
        y_min, y_max = min(ylim), max(ylim)

        current_width = x_max - x_min
        current_height = y_max - y_min

        new_width = current_width * scale
        new_height = current_height * scale

        # Never zoom out past the full original image size
        new_width = min(new_width, home_x_max - home_x_min)
        new_height = min(new_height, home_y_max - home_y_min)

        # Avoid zooming in so far that almost nothing is left visible
        new_width = max(new_width, 5)
        new_height = max(new_height, 5)

        # Keep the point under the cursor at the SAME relative screen position
        # instead of re-centering on it — this way, zooming near an edge just
        # grows the view from there, instead of jumping/panning toward the middle.
        relx = (event.xdata - x_min) / current_width if current_width else 0.5
        rely = (event.ydata - y_min) / current_height if current_height else 0.5
        relx = min(max(relx, 0.0), 1.0)
        rely = min(max(rely, 0.0), 1.0)

        new_x_min = event.xdata - relx * new_width
        new_x_max = new_x_min + new_width

        new_y_min = event.ydata - rely * new_height
        new_y_max = new_y_min + new_height

        # Never let the view go past the actual image bounds (no blank space)
        new_x_min, new_x_max = self._clamp_window(new_x_min, new_x_max, home_x_min, home_x_max)
        new_y_min, new_y_max = self._clamp_window(new_y_min, new_y_max, home_y_min, home_y_max)

        # Preserve each axis' original orientation (the Y axis of an image is
        # normally inverted — imshow draws top row first)
        if self._zoom_home_xlim[0] > self._zoom_home_xlim[1]:
            new_xlim = [new_x_max, new_x_min]
        else:
            new_xlim = [new_x_min, new_x_max]

        if self._zoom_home_ylim[0] > self._zoom_home_ylim[1]:
            new_ylim = [new_y_max, new_y_min]
        else:
            new_ylim = [new_y_min, new_y_max]

        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()

    def reset_zoom(self):
        if self._zoom_home_xlim is None or self._zoom_home_ylim is None:
            return

        self.ax.set_xlim(self._zoom_home_xlim)
        self.ax.set_ylim(self._zoom_home_ylim)
        self.canvas.draw_idle()

    def next_image(self):
        if self.current_index < len(self.csv_files)-1:
            self.current_index += 1
            self.load_current()

    def previous_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current()

    def save_png(self):
        file = filedialog.asksaveasfilename(defaultextension=".png")
        if file:
            self.fig.savefig(file, dpi=300)

    def invert_vertical(self):
        self._invert_current_csv(eixo="vertical")

    def invert_horizontal(self):
        self._invert_current_csv(eixo="horizontal")

    def _invert_current_csv(self, eixo):
        if self.current_data is None or not self.csv_files:
            messagebox.showwarning("Warning", "No image uploaded")
            return

        file = self.csv_files[self.current_index]
        nome_atual = os.path.basename(file)

        rotulo_eixo = "verticalmente (de cima pra baixo)" if eixo == "vertical" else "horizontalmente (da esquerda pra direita)"

        confirmado = messagebox.askyesno(
            "Invert image",
            f"This will rotate the image. {rotulo_eixo} and overwrite the file"
            f"Original CSV ('{nome_atual}'). This action cannot be undone. Do you want to continue?"
        )
        if not confirmado:
            return

        h, w = self.current_data.shape

        if eixo == "vertical":
            self.current_data = np.flipud(self.current_data)
        else:
            self.current_data = np.fliplr(self.current_data)

        try:
            pd.DataFrame(self.current_data).to_csv(file, header=False, index=False)
        except Exception as e:
            messagebox.showerror("Error saving inverted CSV", str(e))
            return

        # Atualiza as coordenadas das anotações desta imagem para acompanhar a
        # inversão, mantendo os rótulos alinhados com a mesma região física.
        for ann in self.annotations:
            if ann["arquivo"] != nome_atual:
                continue

            if eixo == "vertical":
                novo_y0 = h - 1 - ann["y1"]
                novo_y1 = h - 1 - ann["y0"]
                ann["y0"], ann["y1"] = novo_y0, novo_y1
            else:
                novo_x0 = w - 1 - ann["x1"]
                novo_x1 = w - 1 - ann["x0"]
                ann["x0"], ann["x1"] = novo_x0, novo_x1

        self.rewrite_annotation_csv()

        self.selected_annotation_id = None
        self.last_area_pixel_count = None
        if hasattr(self, "delete_area_btn"):
            self.delete_area_btn.config(state="disabled")

        self._cancel_area_creation()
        self._cancel_handle_resize()
        self._cancel_move_annotation()

        self.show_image()

    def show_histogram(self):
        if self.current_data is None:
            return
        plt.figure()
        plt.hist(self.current_data.ravel(), bins=50, color="lightgreen", edgecolor="green", alpha=0.8)
        plt.gcf().set_facecolor("whitesmoke")
        plt.xlabel("Temperature")
        plt.ylabel("Frequency")
        plt.title("Thermal Histogram")
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.show()

    # ------------------------------------------------------------------
    # Seleção de imagens + mover para nova pasta
    # ------------------------------------------------------------------
    def toggle_select_current(self):
        if not self.csv_files:
            return

        file = self.csv_files[self.current_index]

        if file in self.selected_files:
            self.selected_files.remove(file)
        else:
            self.selected_files.add(file)

        self.update_selection_ui()

    def update_selection_ui(self):
        count = len(self.selected_files)

        self.selected_label.config(text=f"Selected images: {count}")

        if count > 0:
            self.move_btn.config(state="normal")
        else:
            self.move_btn.config(state="disabled")

        if self.csv_files:
            file = self.csv_files[self.current_index]
            if file in self.selected_files:
                self.select_btn.config(text="✔ Selected", bg=HIGHLIGHT_COLOR)
            else:
                self.select_btn.config(text="Select", bg=BTN_COLOR)

    def move_selected_images(self):
        if not self.selected_files:
            return

        dest = filedialog.askdirectory(
            title="Select the destination folder"
        )

        if not dest:
            return

        moved = []
        errors = []

        for file in list(self.selected_files):
            try:
                destino_final = os.path.join(dest, os.path.basename(file))
                shutil.move(file, destino_final)
                moved.append(file)
            except Exception as e:
                errors.append(f"{os.path.basename(file)}: {e}")

        for file in moved:
            if file in self.csv_files:
                self.csv_files.remove(file)
            self.selected_files.discard(file)

        if errors:
            messagebox.showerror(
                "Error moving some files",
                "\n".join(errors)
            )

        if moved:
            messagebox.showinfo(
                "Completed",
                f"{len(moved)} file(s) moved to:\n{dest}"
            )

        if not self.csv_files:
            self.current_data = None
            self.filename_label.config(text="No file uploaded")
            self.min_label.config(text="Min: -")
            self.max_label.config(text="Max: -")
            self.mean_label.config(text="Mean: -")
            self.std_label.config(text="Standard deviation: -")
            self.show_error_image()
        else:
            if self.current_index >= len(self.csv_files):
                self.current_index = len(self.csv_files) - 1
            self.load_current()

        self.update_selection_ui()

    # ------------------------------------------------------------------
    # Pular para um arquivo específico
    # ------------------------------------------------------------------
    def jump_to_file(self):
        if not self.csv_files:
            messagebox.showwarning("Warning", "No file uploaded")
            return

        nome = simpledialog.askstring(
            "Skip to image",
            "Enter the CSV file name:",
            parent=self.root
        )

        if not nome:
            return

        alvo = nome.strip().lower()

        # Primeiro tenta correspondência exata do nome do arquivo
        for i, file in enumerate(self.csv_files):
            if os.path.basename(file).lower() == alvo:
                self.current_index = i
                self.load_current()
                return

        # Depois tenta correspondência parcial
        for i, file in enumerate(self.csv_files):
            if alvo in os.path.basename(file).lower():
                self.current_index = i
                self.load_current()
                return

        messagebox.showerror(
            "Not found",
            f"No files found with '{nome}'."
        )

    # ------------------------------------------------------------------
    # Modo de seleção de área (Retangular / Elipse)
    # ------------------------------------------------------------------
    def apply_fixed_size_to_selected(self, event=None):
        # Só se aplica quando "Área fixa" está marcada e há uma área destacada
        if not self.area_fixa_var.get():
            return
        if self.selected_annotation_id is None:
            return
        if self.current_data is None:
            return

        ann = self._find_annotation_by_id(self.selected_annotation_id)
        if ann is None:
            return

        try:
            largura_fixa = max(1, int(float(self.largura_fixa_entry.get())))
        except Exception:
            return

        try:
            altura_fixa = max(1, int(float(self.altura_fixa_entry.get())))
        except Exception:
            return

        if ann["forma"] == "ellipse":
            # Elipse é sempre um círculo: usa o maior valor para largura e altura
            diametro = max(largura_fixa, altura_fixa)
            largura_fixa = diametro
            altura_fixa = diametro

        h, w = self.current_data.shape

        x0 = ann["x0"]
        y0 = ann["y0"]
        x1 = min(w - 1, x0 + largura_fixa)
        y1 = min(h - 1, y0 + altura_fixa)

        if x1 <= x0 or y1 <= y0:
            return

        ann["x0"], ann["y0"], ann["x1"], ann["y1"] = x0, y0, x1, y1

        self._redraw_single_annotation(ann)

        self.rewrite_annotation_csv()

        largura_px = x1 - x0 + 1
        altura_px = y1 - y0 + 1
        self.last_area_pixel_count = largura_px * altura_px

        self.status.config(
            text=(
                f"Selected area ({ann['classe']}): {largura_px}×{altura_px} = "
                f"{self.last_area_pixel_count} pixels"
            )
        )

        if self.ajustar_mode and self.selected_annotation_id == ann["id"]:
            self._show_resize_handles(ann)

        self.canvas.draw_idle()

    def toggle_area_color(self):
        global area_color

        if area_color == "white":
            area_color = "black"
            self.area_color_btn.config(text="⚫ Black", bg="black", fg="white")
        else:
            area_color = "white"
            self.area_color_btn.config(text="⚪ White", bg="white", fg="black")

        # Atualiza as áreas já desenhadas na imagem atual (exceto a destacada
        # para deleção, que continua em vermelho)
        for ann_id, (patch, text_obj, ann) in self.annotation_patches.items():
            destacado = (ann_id == self.selected_annotation_id)
            if not destacado:
                patch.set_edgecolor(area_color)
                patch.set_facecolor(area_color)

        self._update_canvas_cursor()

        self.canvas.draw_idle()

    def _update_canvas_cursor(self):
        # Cursor em cruz sobre a imagem, na mesma cor escolhida para as áreas
        global area_color

        cor_cruz = "white" if area_color == "black" else "black"
        cor_fundo = "black" if area_color == "black" else "white"

        widget = self.canvas.get_tk_widget()

        try:
            #widget.config(cursor=f"cross {cor_cruz} {cor_fundo}")
            widget.config(cursor=f"crosshair")  #plus cross tcross crosshair 
        except Exception:
            try:
                widget.config(cursor="cross")
            except Exception:
                pass

    def disable_ajustar_mode(self):
        if self.ajustar_mode:
            self.ajustar_mode = False
            if hasattr(self, "ajustar_btn"):
                self.ajustar_btn.config(bg=BTN_COLOR)

        self._cancel_handle_resize()
        self._cancel_move_annotation()
        self._hide_resize_handles()

    def toggle_ajustar_mode(self):
        self.ajustar_mode = not self.ajustar_mode

        if self.ajustar_mode:
            # Desativa Retangular/Elipse enquanto o modo Ajustar estiver ativo,
            # evitando que os dois modos de interação com o mouse se conflitem.
            self.area_mode = None
            self.rect_mode_btn.config(bg=BTN_COLOR)
            self.ellipse_mode_btn.config(bg=BTN_COLOR)
            self._cancel_area_creation()
            self.ajustar_btn.config(bg=HIGHLIGHT_COLOR)

            ann = self._find_annotation_by_id(self.selected_annotation_id)
            if ann is not None:
                self._show_resize_handles(ann)
        else:
            self.ajustar_btn.config(bg=BTN_COLOR)
            self._cancel_handle_resize()
            self._cancel_move_annotation()
            self._hide_resize_handles()

    def set_area_mode(self, mode):
        if mode == self.area_mode:
            mode = None  # clicar novamente no mesmo modo desativa

        if mode not in (None, "rect", "ellipse"):
            return

        if mode is not None and self.ajustar_mode:
            # Ativar Retangular/Elipse desliga o modo Ajustar
            self.ajustar_mode = False
            if hasattr(self, "ajustar_btn"):
                self.ajustar_btn.config(bg=BTN_COLOR)
            self._cancel_handle_resize()
            self._cancel_move_annotation()
            self._hide_resize_handles()

        self._cancel_area_creation()

        self.area_mode = mode

        self.rect_mode_btn.config(bg=HIGHLIGHT_COLOR if mode == "rect" else BTN_COLOR)
        self.ellipse_mode_btn.config(bg=HIGHLIGHT_COLOR if mode == "ellipse" else BTN_COLOR)


    # ------------------------------------------------------------------
    # Desenho das anotações (retângulos/elipses + rótulo translúcido)
    # ------------------------------------------------------------------
    def _create_annotation_artist(self, ann):
        x0, y0, x1, y1 = ann["x0"], ann["y0"], ann["x1"], ann["y1"]
        w = max(x1 - x0, 1)
        h = max(y1 - y0, 1)
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0

        destacado = (ann["id"] == self.selected_annotation_id)
        edge = "red" if destacado else area_color
        lw = 2.4 if destacado else 1.2
        ls = "--" if destacado else "-"

        if ann["forma"] == "ellipse":
            patch = MplEllipsePatch(
                (cx, cy), width=w, height=h,
                edgecolor=edge, facecolor=area_color, alpha=0.21,
                linewidth=lw, linestyle=ls
            )
        else:
            patch = MplRectangle(
                (x0, y0), w, h,
                edgecolor=edge, facecolor=area_color, alpha=0.21,
                linewidth=lw, linestyle=ls
            )

        self.ax.add_patch(patch)

        text_obj = self.ax.text(
            cx, cy, ann["classe"],
            color="white", fontsize=8, alpha=0.7,
            ha="center", va="center"
        )

        return patch, text_obj

    def draw_annotations(self):
        self.annotation_patches = {}

        if self.current_data is None or not self.csv_files:
            return

        nome_atual = os.path.basename(self.csv_files[self.current_index])

        for ann in self.annotations:
            if ann["arquivo"] != nome_atual:
                continue
            patch, text_obj = self._create_annotation_artist(ann)
            self.annotation_patches[ann["id"]] = (patch, text_obj, ann)

    def add_annotation_artist(self, ann):
        patch, text_obj = self._create_annotation_artist(ann)
        self.annotation_patches[ann["id"]] = (patch, text_obj, ann)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Clique para destacar / desmarcar área (modo de deleção)
    # ------------------------------------------------------------------
    def on_canvas_press(self, event):
        self._press_xy = (event.xdata, event.ydata)

        if getattr(event, "dblclick", False):
            self.reset_zoom()
            return

        if event.xdata is None or event.ydata is None:
            return

        # Modo Ajustar: se o clique caiu sobre um handle de redimensionamento,
        # inicia o arrasto de ajuste (com pré-visualização ao vivo)
        if self.ajustar_mode and self.selected_annotation_id is not None:
            handle = self._find_handle_at(event.xdata, event.ydata)
            if handle is not None:
                self._start_handle_resize(handle)
                return

            # Não pegou nenhum handle: se o clique caiu dentro da própria área
            # selecionada, permite mover a área inteira arrastando
            ann = self._find_annotation_by_id(self.selected_annotation_id)
            if ann is not None and self._point_inside_ann(event.xdata, event.ydata, ann):
                self._start_move_annotation(event.xdata, event.ydata)
                return

        # Modo de criação de área (Retangular/Elipse): inicia o desenho com
        # pré-visualização ao vivo
        if self.area_mode is not None and self.current_data is not None:
            self._start_area_creation(event.xdata, event.ydata)

    def on_canvas_release(self, event):
        x_press, y_press = self._press_xy if self._press_xy else (None, None)
        self._press_xy = None

        if self._resizing:
            self._finish_handle_resize(event)
            return

        if self._moving:
            self._finish_move_annotation(event)
            return

        if self._creating:
            self._finish_area_creation(event)
            return

        if self.current_data is None:
            return

        if event.xdata is None or event.ydata is None or x_press is None or y_press is None:
            return

        dx = event.xdata - x_press
        dy = event.ydata - y_press

        if self.ajustar_mode:
            # Clique simples (sem ter pego um handle): troca a área selecionada
            ann_id = self.find_annotation_at(event.xdata, event.ydata)

            if ann_id is None:
                self.clear_annotation_highlight()
            else:
                self.select_annotation_for_deletion(ann_id)
            return

        if abs(dx) > 3 or abs(dy) > 3:
            return  # não deveria ocorrer (criação já é tratada acima), mas por segurança

        ann_id = self.find_annotation_at(event.xdata, event.ydata)

        if ann_id is None:
            self.clear_annotation_highlight()
        else:
            self.select_annotation_for_deletion(ann_id)

    # ------------------------------------------------------------------
    # Criação de área com pré-visualização ao vivo
    # ------------------------------------------------------------------
    def _cancel_area_creation(self):
        if self._create_preview_patch is not None:
            try:
                self._create_preview_patch.remove()
            except Exception:
                pass
            self._create_preview_patch = None

        self._creating = False
        self._create_start = None

    def _start_area_creation(self, x, y):
        if x is None or y is None:
            return

        self._creating = True
        self._create_start = (x, y)

        estilo = dict(
            edgecolor="yellow", facecolor=area_color, alpha=0.25,
            linewidth=1.6, linestyle="--"
        )

        if self.area_mode == "ellipse":
            patch = MplEllipsePatch((x, y), width=1, height=1, **estilo)
        else:
            patch = MplRectangle((x, y), 1, 1, **estilo)

        self.ax.add_patch(patch)
        self._create_preview_patch = patch
        self.canvas.draw_idle()

    def _compute_create_bounds(self, x_atual, y_atual):
        if self._create_start is None or self.current_data is None:
            return None

        x0_clique, y0_clique = self._create_start
        if x_atual is None:
            x_atual = x0_clique
        if y_atual is None:
            y_atual = y0_clique

        h, w = self.current_data.shape

        if self.area_fixa_var.get():
            try:
                largura_fixa = max(1, int(float(self.largura_fixa_entry.get())))
            except Exception:
                largura_fixa = 20
            try:
                altura_fixa = max(1, int(float(self.altura_fixa_entry.get())))
            except Exception:
                altura_fixa = 20

            if self.area_mode == "ellipse":
                diametro = max(largura_fixa, altura_fixa)
                largura_fixa = diametro
                altura_fixa = diametro

            largura_fixa = min(largura_fixa, w - 1)
            altura_fixa = min(altura_fixa, h - 1)

            if x_atual >= x0_clique:
                x0, x1 = float(x0_clique), float(x0_clique + largura_fixa)
            else:
                x0, x1 = float(x0_clique - largura_fixa), float(x0_clique)

            if y_atual >= y0_clique:
                y0, y1 = float(y0_clique), float(y0_clique + altura_fixa)
            else:
                y0, y1 = float(y0_clique - altura_fixa), float(y0_clique)
        else:
            x0, x1 = sorted([float(x0_clique), float(x_atual)])
            y0, y1 = sorted([float(y0_clique), float(y_atual)])

            if self.area_mode == "ellipse":
                # Elipse é sempre um círculo, já durante a pré-visualização
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                raio = max((x1 - x0) / 2.0, (y1 - y0) / 2.0, 0.5)
                raio = min(raio, (w - 1) / 2.0, (h - 1) / 2.0)
                x0, x1 = cx - raio, cx + raio
                y0, y1 = cy - raio, cy + raio

        # Desloca (sem deformar) caso a caixa ultrapasse os limites da imagem
        if x0 < 0:
            x1 -= x0
            x0 = 0.0
        if x1 > w - 1:
            x0 -= (x1 - (w - 1))
            x1 = float(w - 1)
        if y0 < 0:
            y1 -= y0
            y0 = 0.0
        if y1 > h - 1:
            y0 -= (y1 - (h - 1))
            y1 = float(h - 1)

        x0 = max(0.0, x0)
        x1 = min(float(w - 1), x1)
        y0 = max(0.0, y0)
        y1 = min(float(h - 1), y1)

        return (x0, y0, x1, y1)

    def _update_create_preview(self, event):
        if self._create_preview_patch is None:
            return

        bounds = self._compute_create_bounds(event.xdata, event.ydata)
        if bounds is None:
            return

        x0, y0, x1, y1 = bounds
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        largura = max(x1 - x0, 0.5)
        altura = max(y1 - y0, 0.5)

        if self.area_mode == "ellipse":
            self._create_preview_patch.center = (cx, cy)
            self._create_preview_patch.width = largura
            self._create_preview_patch.height = altura
        else:
            self._create_preview_patch.set_xy((x0, y0))
            self._create_preview_patch.set_width(largura)
            self._create_preview_patch.set_height(altura)

        self.canvas.draw_idle()

    def _finish_area_creation(self, event):
        bounds = self._compute_create_bounds(event.xdata, event.ydata)

        self._cancel_area_creation()
        self.canvas.draw_idle()

        if bounds is None or self.current_data is None:
            return

        h, w = self.current_data.shape
        x0, y0, x1, y1 = bounds

        xi0 = max(0, int(round(x0)))
        xi1 = min(w - 1, int(round(x1)))
        yi0 = max(0, int(round(y0)))
        yi1 = min(h - 1, int(round(y1)))

        if xi1 <= xi0 or yi1 <= yi0:
            return

        if not self.classes:
            self.open_class_manager()

            if not self.classes:
                return  # usuário fechou o gerenciador sem definir nenhuma classe

        classe = self.ask_class_dialog()
        if not classe:
            return

        ann = {
            "id": uuid.uuid4().hex[:10],
            "arquivo": os.path.basename(self.csv_files[self.current_index]),
            "classe": classe,
            "forma": self.area_mode,
            "x0": xi0,
            "y0": yi0,
            "x1": xi1,
            "y1": yi1,
        }

        self.annotations.append(ann)
        self.append_annotation_to_csv(ann)
        self.add_annotation_artist(ann)

        # A área recém-criada passa a ser a "área selecionada"
        self.select_annotation_for_deletion(ann["id"])

    # ------------------------------------------------------------------
    # Handles de redimensionamento (modo Ajustar) com pré-visualização ao vivo
    # ------------------------------------------------------------------
    def _handle_positions(self, ann):
        x0, y0, x1, y1 = ann["x0"], ann["y0"], ann["x1"], ann["y1"]
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        return {
            "esquerda": (x0, cy),
            "direita": (x1, cy),
            "topo": (cx, y0),
            "fundo": (cx, y1),
        }

    def _show_resize_handles(self, ann):
        self._hide_resize_handles()

        for nome, (hx, hy) in self._handle_positions(ann).items():
            artista, = self.ax.plot(
                [hx], [hy],
                marker="s", markersize=2,
                markerfacecolor="yellow", markeredgecolor="black",
                linestyle="None", zorder=10
            )
            self._handle_artists[nome] = artista

        self.canvas.draw_idle()

    def _hide_resize_handles(self):
        for artista in self._handle_artists.values():
            try:
                artista.remove()
            except Exception:
                pass
        self._handle_artists = {}

    def _find_handle_at(self, x, y):
        if not self._handle_artists:
            return None

        ann = self._find_annotation_by_id(self.selected_annotation_id)
        if ann is None:
            return None

        raio_deteccao = max(3, 0.06 * max(ann["x1"] - ann["x0"], ann["y1"] - ann["y0"], 1))

        mais_proximo = None
        menor_dist = None
        for nome, (hx, hy) in self._handle_positions(ann).items():
            dist = ((x - hx) ** 2 + (y - hy) ** 2) ** 0.5
            if dist <= raio_deteccao and (menor_dist is None or dist < menor_dist):
                menor_dist = dist
                mais_proximo = nome

        return mais_proximo

    def _cancel_handle_resize(self):
        self._resizing = False
        self._resize_handle_active = None
        self._resize_center = None
        self._resize_orig_bounds = None
        self._resize_live_bounds = None

    # ------------------------------------------------------------------
    # Mover (arrastar) uma área já existente, clicando dentro dela
    # ------------------------------------------------------------------
    def _point_inside_ann(self, x, y, ann):
        x0, y0, x1, y1 = ann["x0"], ann["y0"], ann["x1"], ann["y1"]

        if ann["forma"] == "ellipse":
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0
            rx = max((x1 - x0) / 2.0, 1e-6)
            ry = max((y1 - y0) / 2.0, 1e-6)
            return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0

        return (x0 <= x <= x1) and (y0 <= y <= y1)

    def _cancel_move_annotation(self):
        self._moving = False
        self._move_start = None
        self._move_orig_bounds = None
        self._move_live_bounds = None

    def _start_move_annotation(self, x, y):
        ann = self._find_annotation_by_id(self.selected_annotation_id)
        if ann is None:
            return

        self._moving = True
        self._move_start = (x, y)
        self._move_orig_bounds = (ann["x0"], ann["y0"], ann["x1"], ann["y1"])
        self._move_live_bounds = self._move_orig_bounds

    def _update_move_preview(self, event):
        if event.xdata is None or event.ydata is None:
            return
        if self._move_start is None or self._move_orig_bounds is None:
            return

        dx = event.xdata - self._move_start[0]
        dy = event.ydata - self._move_start[1]

        x0o, y0o, x1o, y1o = self._move_orig_bounds

        novo_x0 = x0o + dx
        novo_x1 = x1o + dx
        novo_y0 = y0o + dy
        novo_y1 = y1o + dy

        # Mantém a área inteira dentro dos limites da imagem, sem deformar
        if self.current_data is not None:
            h, w = self.current_data.shape
            if novo_x0 < 0:
                novo_x1 -= novo_x0
                novo_x0 = 0.0
            if novo_x1 > w - 1:
                novo_x0 -= (novo_x1 - (w - 1))
                novo_x1 = float(w - 1)
            if novo_y0 < 0:
                novo_y1 -= novo_y0
                novo_y0 = 0.0
            if novo_y1 > h - 1:
                novo_y0 -= (novo_y1 - (h - 1))
                novo_y1 = float(h - 1)

        self._move_live_bounds = (novo_x0, novo_y0, novo_x1, novo_y1)

        ann = self._find_annotation_by_id(self.selected_annotation_id)
        entry = self.annotation_patches.get(self.selected_annotation_id)
        if ann is None or entry is None:
            return

        patch, text_obj, _ann = entry
        cx = (novo_x0 + novo_x1) / 2.0
        cy = (novo_y0 + novo_y1) / 2.0
        largura_atual = max(novo_x1 - novo_x0, 1.0)
        altura_atual = max(novo_y1 - novo_y0, 1.0)

        if ann["forma"] == "ellipse":
            patch.center = (cx, cy)
            patch.width = largura_atual
            patch.height = altura_atual
        else:
            patch.set_xy((novo_x0, novo_y0))
            patch.set_width(largura_atual)
            patch.set_height(altura_atual)

        text_obj.set_position((cx, cy))

        ann_temp = dict(ann)
        ann_temp["x0"], ann_temp["y0"], ann_temp["x1"], ann_temp["y1"] = novo_x0, novo_y0, novo_x1, novo_y1
        for nome, (hx, hy) in self._handle_positions(ann_temp).items():
            if nome in self._handle_artists:
                self._handle_artists[nome].set_data([hx], [hy])

        self.canvas.draw_idle()

    def _finish_move_annotation(self, event):
        bounds = self._move_live_bounds
        orig_bounds = self._move_orig_bounds
        ann = self._find_annotation_by_id(self.selected_annotation_id)

        self._cancel_move_annotation()

        if bounds is None or ann is None or self.current_data is None:
            return

        if (
            orig_bounds is not None
            and abs(bounds[0] - orig_bounds[0]) < 0.5
            and abs(bounds[1] - orig_bounds[1]) < 0.5
        ):
            # Foi só um clique, sem arrasto real: não altera nada
            self._redraw_single_annotation(ann)
            if self.ajustar_mode:
                self._show_resize_handles(ann)
            return

        h, w = self.current_data.shape
        novo_x0 = max(0, int(round(bounds[0])))
        novo_x1 = min(w - 1, int(round(bounds[2])))
        novo_y0 = max(0, int(round(bounds[1])))
        novo_y1 = min(h - 1, int(round(bounds[3])))

        if novo_x1 <= novo_x0 or novo_y1 <= novo_y0:
            self._redraw_single_annotation(ann)
            if self.ajustar_mode:
                self._show_resize_handles(ann)
            return

        ann["x0"], ann["y0"], ann["x1"], ann["y1"] = novo_x0, novo_y0, novo_x1, novo_y1

        self._redraw_single_annotation(ann)
        self.rewrite_annotation_csv()

        largura_px = novo_x1 - novo_x0 + 1
        altura_px = novo_y1 - novo_y0 + 1
        self.last_area_pixel_count = largura_px * altura_px

        self.status.config(
            text=(
                f"Área movida ({ann['classe']}): {largura_px}×{altura_px} = "
                f"{self.last_area_pixel_count} pixels"
            )
        )

        if self.ajustar_mode:
            self._show_resize_handles(ann)

    def _start_handle_resize(self, handle):
        ann = self._find_annotation_by_id(self.selected_annotation_id)
        if ann is None:
            return

        self._resizing = True
        self._resize_handle_active = handle

        x0, y0, x1, y1 = ann["x0"], ann["y0"], ann["x1"], ann["y1"]
        self._resize_center = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        self._resize_orig_bounds = (x0, y0, x1, y1)
        self._resize_live_bounds = (x0, y0, x1, y1)

    def _compute_resize_bounds(self, event_x, event_y):
        ann = self._find_annotation_by_id(self.selected_annotation_id)
        if ann is None or self._resize_center is None or self._resize_orig_bounds is None:
            return None

        if event_x is None or event_y is None:
            return self._resize_live_bounds

        cx, cy = self._resize_center
        x0o, y0o, x1o, y1o = self._resize_orig_bounds
        meia_largura_orig = (x1o - x0o) / 2.0
        meia_altura_orig = (y1o - y0o) / 2.0

        if ann["forma"] == "ellipse":
            # Círculo: o raio segue diretamente a distância do cursor ao centro,
            # no eixo do handle arrastado — assim dá pra crescer OU encolher
            # livremente (usar o maior valor "congelado" impediria encolher).
            if self._resize_handle_active in ("esquerda", "direita"):
                raio = max(1.0, abs(event_x - cx))
            else:
                raio = max(1.0, abs(event_y - cy))
            meia_largura = raio
            meia_altura = raio
        else:
            if self._resize_handle_active in ("esquerda", "direita"):
                meia_largura = max(1.0, abs(event_x - cx))
                meia_altura = meia_altura_orig
            else:
                meia_largura = meia_largura_orig
                meia_altura = max(1.0, abs(event_y - cy))

        novo_x0 = cx - meia_largura
        novo_x1 = cx + meia_largura
        novo_y0 = cy - meia_altura
        novo_y1 = cy + meia_altura

        if self.current_data is not None:
            h, w = self.current_data.shape
            novo_x0 = max(0.0, novo_x0)
            novo_x1 = min(float(w - 1), novo_x1)
            novo_y0 = max(0.0, novo_y0)
            novo_y1 = min(float(h - 1), novo_y1)

        return (novo_x0, novo_y0, novo_x1, novo_y1)

    def _update_handle_resize_preview(self, event):
        bounds = self._compute_resize_bounds(event.xdata, event.ydata)
        if bounds is None:
            return

        self._resize_live_bounds = bounds
        x0, y0, x1, y1 = bounds

        ann = self._find_annotation_by_id(self.selected_annotation_id)
        entry = self.annotation_patches.get(self.selected_annotation_id)
        if ann is None or entry is None:
            return

        patch, text_obj, _ann = entry
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        largura = max(x1 - x0, 1.0)
        altura = max(y1 - y0, 1.0)

        if ann["forma"] == "ellipse":
            patch.center = (cx, cy)
            patch.width = largura
            patch.height = altura
        else:
            patch.set_xy((x0, y0))
            patch.set_width(largura)
            patch.set_height(altura)

        text_obj.set_position((cx, cy))

        ann_temp = dict(ann)
        ann_temp["x0"], ann_temp["y0"], ann_temp["x1"], ann_temp["y1"] = x0, y0, x1, y1
        for nome, (hx, hy) in self._handle_positions(ann_temp).items():
            if nome in self._handle_artists:
                self._handle_artists[nome].set_data([hx], [hy])

        self.canvas.draw_idle()

    def _redraw_single_annotation(self, ann):
        entry = self.annotation_patches.pop(ann["id"], None)
        if entry:
            old_patch, old_text, _a = entry
            try:
                old_patch.remove()
                old_text.remove()
            except Exception:
                pass

        patch, text_obj = self._create_annotation_artist(ann)
        self.annotation_patches[ann["id"]] = (patch, text_obj, ann)
        self.canvas.draw_idle()

    def _finish_handle_resize(self, event):
        bounds = self._compute_resize_bounds(event.xdata, event.ydata)
        if bounds is None:
            bounds = self._resize_live_bounds

        ann = self._find_annotation_by_id(self.selected_annotation_id)

        self._cancel_handle_resize()
        self._cancel_move_annotation()

        if bounds is None or ann is None or self.current_data is None:
            return

        h, w = self.current_data.shape
        novo_x0 = max(0, int(round(bounds[0])))
        novo_x1 = min(w - 1, int(round(bounds[2])))
        novo_y0 = max(0, int(round(bounds[1])))
        novo_y1 = min(h - 1, int(round(bounds[3])))

        if novo_x1 <= novo_x0 or novo_y1 <= novo_y0:
            self._redraw_single_annotation(ann)
            if self.ajustar_mode:
                self._show_resize_handles(ann)
            return

        ann["x0"], ann["y0"], ann["x1"], ann["y1"] = novo_x0, novo_y0, novo_x1, novo_y1

        self._redraw_single_annotation(ann)
        self.rewrite_annotation_csv()

        largura_px = novo_x1 - novo_x0 + 1
        altura_px = novo_y1 - novo_y0 + 1
        self.last_area_pixel_count = largura_px * altura_px

        self.status.config(
            text=(
                f"Adjusted area ({ann['classe']}): {largura_px}×{altura_px} = "
                f"{self.last_area_pixel_count} pixels"
            )
        )

        if self.ajustar_mode:
            self._show_resize_handles(ann)

    def find_annotation_at(self, x, y):
        for ann_id, (patch, text_obj, ann) in reversed(list(self.annotation_patches.items())):
            x0, y0, x1, y1 = ann["x0"], ann["y0"], ann["x1"], ann["y1"]

            if ann["forma"] == "ellipse":
                cx = (x0 + x1) / 2.0
                cy = (y0 + y1) / 2.0
                rx = max((x1 - x0) / 2.0, 1e-6)
                ry = max((y1 - y0) / 2.0, 1e-6)
                dentro = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0
            else:
                dentro = (x0 <= x <= x1) and (y0 <= y <= y1)

            if dentro:
                return ann_id

        return None

    def select_annotation_for_deletion(self, ann_id):
        self.selected_annotation_id = ann_id
        self.delete_area_btn.config(state="normal")
        self.refresh_annotation_highlight()

        ann = self._find_annotation_by_id(ann_id)
        if ann is None:
            return

        largura_px = ann["x1"] - ann["x0"] + 1
        altura_px = ann["y1"] - ann["y0"] + 1
        self.last_area_pixel_count = largura_px * altura_px

        self.status.config(
            text=(
                f"Selected area ({ann['classe']}): {largura_px}×{altura_px} = "
                f"{self.last_area_pixel_count} pixels"
            )
        )

        # Se o modo "Área fixa" estiver ativo, mostra nos campos o tamanho
        # atual desta área, permitindo editá-los para redimensioná-la.
        if self.area_fixa_var.get():
            self.largura_fixa_entry.delete(0, "end")
            self.largura_fixa_entry.insert(0, str(ann["x1"] - ann["x0"]))

            self.altura_fixa_entry.delete(0, "end")
            self.altura_fixa_entry.insert(0, str(ann["y1"] - ann["y0"]))

        # Em modo Ajustar, mostra os pontos (handles) para redimensionar
        # arrastando as bordas, com centro fixo
        if self.ajustar_mode:
            self._show_resize_handles(ann)

    def clear_annotation_highlight(self):
        if self.selected_annotation_id is None:
            return

        self.selected_annotation_id = None
        self.delete_area_btn.config(state="disabled")
        self.last_area_pixel_count = None
        self._hide_resize_handles()
        self.refresh_annotation_highlight()

    def _find_annotation_by_id(self, ann_id):
        for a in self.annotations:
            if a["id"] == ann_id:
                return a
        return None

    def refresh_annotation_highlight(self):
        global area_color

        for ann_id, (patch, text_obj, ann) in self.annotation_patches.items():
            destacado = (ann_id == self.selected_annotation_id)
            patch.set_edgecolor("red" if destacado else area_color)
            patch.set_facecolor(area_color)
            patch.set_linewidth(2.4 if destacado else 1.2)
            patch.set_linestyle("--" if destacado else "-")

        self.canvas.draw_idle()

    def delete_selected_annotation(self):
        if self.selected_annotation_id is None:
            return

        ann_id = self.selected_annotation_id

        self._hide_resize_handles()
        self._cancel_handle_resize()
        self._cancel_move_annotation()

        self.annotations = [a for a in self.annotations if a["id"] != ann_id]

        entry = self.annotation_patches.pop(ann_id, None)
        if entry:
            patch, text_obj, _ann = entry
            try:
                patch.remove()
                text_obj.remove()
            except Exception:
                pass

        self.selected_annotation_id = None
        self.delete_area_btn.config(state="disabled")

        self.rewrite_annotation_csv()

        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Persistência em annotation_areas.csv
    # ------------------------------------------------------------------
    def load_annotations_for_folder(self, folder):
        nome_arquivo = self._annotation_filename_for_folder(folder)
        self.annotation_csv_path = os.path.join(folder, nome_arquivo)

        if os.path.exists(self.annotation_csv_path):
            try:
                df = pd.read_csv(self.annotation_csv_path, dtype=str)

                if "id" not in df.columns:
                    df.insert(0, "id", [uuid.uuid4().hex[:10] for _ in range(len(df))])

                for col in self.ANNOTATION_COLUMNS:
                    if col not in df.columns:
                        df[col] = ""

                df = df[self.ANNOTATION_COLUMNS]
                df = df.dropna(subset=["arquivo", "classe", "forma", "x0", "y0", "x1", "y1"])

                registros = []
                for _, row in df.iterrows():
                    try:
                        registros.append({
                            "id": str(row["id"]),
                            "arquivo": str(row["arquivo"]),
                            "classe": str(row["classe"]),
                            "forma": str(row["forma"]),
                            "x0": int(float(row["x0"])),
                            "y0": int(float(row["y0"])),
                            "x1": int(float(row["x1"])),
                            "y1": int(float(row["y1"])),
                        })
                    except Exception:
                        continue

                self.annotations = registros
                self.classes = sorted({a["classe"] for a in self.annotations if a["classe"]})

            except Exception as e:
                messagebox.showwarning(
                    "Warning",
                    f"Unable to read {nome_arquivo}:\n{e}"
                )
                self.annotations = []
                self.classes = []
        else:
            self.annotations = []
            self.classes = []
            try:
                pd.DataFrame(columns=self.ANNOTATION_COLUMNS).to_csv(
                    self.annotation_csv_path, index=False
                )
            except Exception as e:
                messagebox.showwarning(
                    "Warning",
                    f"Could not create {nome_arquivo}:\n{e}"
                )

    def append_annotation_to_csv(self, ann):
        if not self.annotation_csv_path:
            return

        linha = {col: ann[col] for col in self.ANNOTATION_COLUMNS}

        try:
            escrever_cabecalho = (
                not os.path.exists(self.annotation_csv_path)
                or os.path.getsize(self.annotation_csv_path) == 0
            )
            pd.DataFrame([linha], columns=self.ANNOTATION_COLUMNS).to_csv(
                self.annotation_csv_path, mode="a", header=escrever_cabecalho, index=False
            )
        except Exception as e:
            messagebox.showerror("Error saving annotation", str(e))

    def rewrite_annotation_csv(self):
        if not self.annotation_csv_path:
            return

        try:
            pd.DataFrame(self.annotations, columns=self.ANNOTATION_COLUMNS).to_csv(
                self.annotation_csv_path, index=False
            )
        except Exception as e:
            messagebox.showerror("Error updating notes", str(e))

    # ------------------------------------------------------------------
    # Gerenciador de classes
    # ------------------------------------------------------------------
    def open_class_manager(self):
        win = tk.Toplevel(self.root)
        win.title("Define labels")
        win.configure(bg=BG_PANEL)
        win.geometry("300x420")
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win, text="Labeling classes", bg=BG_PANEL, fg="black",
            font=("Arial", 11, "bold")
        ).pack(pady=(10, 5))

        listbox = tk.Listbox(win, height=10)
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        for c in self.classes:
            listbox.insert("end", c)

        entry_frame = tk.Frame(win, bg=BG_PANEL)
        entry_frame.pack(fill="x", padx=10, pady=5)

        entry = tk.Entry(entry_frame)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def add_class():
            nome = entry.get().strip()
            if not nome:
                return
            if nome in self.classes:
                messagebox.showinfo("Warning", "This class already exists", parent=win)
                return
            self.classes.append(nome)
            listbox.insert("end", nome)
            entry.delete(0, "end")

        tk.Button(entry_frame, text="Add", bg=BTN_COLOR, command=add_class).pack(side="left")
        entry.bind("<Return>", lambda e: add_class())

        def alter_class():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo(
                    "Warning", "Select a class from the list to modify", parent=win
                )
                return

            nome_antigo = listbox.get(sel[0])

            novo_nome = simpledialog.askstring(
                "Change label",
                f"New label for'{nome_antigo}':",
                initialvalue=nome_antigo,
                parent=win
            )

            if not novo_nome:
                return

            novo_nome = novo_nome.strip()

            if not novo_nome or novo_nome == nome_antigo:
                return

            if novo_nome in self.classes:
                confirmado = messagebox.askyesno(
                    "Classes will be combined",
                    f"A class named '{novo_nome}' already exists \n"
                    f"All areas labeled as '{nome_antigo}' will start using "
                    f"'{novo_nome}'. Do you want to continue?",
                    parent=win
                )
            else:
                confirmado = messagebox.askyesno(
                    "Confirm change",
                    f"This will replace the label '{nome_antigo}' with '{novo_nome}' in "
                    "ALL areas are already marked with this class. Do you want to continue?",
                    parent=win
                )

            if not confirmado:
                return

            self.rename_class(nome_antigo, novo_nome)

            listbox.delete(0, "end")
            for c in self.classes:
                listbox.insert("end", c)

        def remove_class():
            sel = listbox.curselection()
            if not sel:
                return

            nome = listbox.get(sel[0])
            qtd = sum(1 for a in self.annotations if a["classe"] == nome)

            if qtd > 0:
                msg = (
                    f"Remove the label '{nome}'?\n\n"
                    f"This will also erase {qtd} area(s) marked with this label "
                    "on all images in the current folder. This action cannot be undone."
                )
            else:
                msg = f"Remove the label '{nome}' from the list?"

            if not messagebox.askyesno("Remove label", msg, parent=win):
                return

            self.classes.remove(nome)
            listbox.delete(sel[0])

            if qtd > 0:
                self.remove_annotations_by_class(nome)

        btn_frame = tk.Frame(win, bg=BG_PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 5))

        tk.Button(btn_frame, text="Change label", bg=BTN_COLOR, command=alter_class).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        tk.Button(btn_frame, text="Remove selected label", bg=BTN_COLOR, command=remove_class).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        tk.Button(win, text="Close", bg=BTN_COLOR, command=win.destroy).pack(pady=(0, 10))

        entry.focus_set()

        self.root.wait_window(win)

    def rename_class(self, nome_antigo, nome_novo):
        nome_antigo = nome_antigo.strip()
        nome_novo = nome_novo.strip()

        if not nome_novo or nome_novo == nome_antigo:
            return

        for ann in self.annotations:
            if ann["classe"] == nome_antigo:
                ann["classe"] = nome_novo

        if nome_antigo in self.classes:
            self.classes.remove(nome_antigo)
        if nome_novo not in self.classes:
            self.classes.append(nome_novo)
        self.classes.sort()

        for ann_id, (patch, text_obj, ann) in self.annotation_patches.items():
            if ann["classe"] == nome_novo:
                text_obj.set_text(nome_novo)

        self.rewrite_annotation_csv()
        self.canvas.draw_idle()

    def remove_annotations_by_class(self, classe):
        self.annotations = [a for a in self.annotations if a["classe"] != classe]

        para_remover = [
            ann_id for ann_id, (_p, _t, ann) in self.annotation_patches.items()
            if ann["classe"] == classe
        ]

        for ann_id in para_remover:
            patch, text_obj, _ann = self.annotation_patches.pop(ann_id)
            try:
                patch.remove()
                text_obj.remove()
            except Exception:
                pass

            if ann_id == self.selected_annotation_id:
                self.selected_annotation_id = None
                self.delete_area_btn.config(state="disabled")

        self.rewrite_annotation_csv()
        self.canvas.draw_idle()

    def ask_class_dialog(self):
        resultado = {"classe": None}

        win = tk.Toplevel(self.root)
        win.title("Label area")
        win.configure(bg=BG_PANEL)
        win.geometry("260x340")
        win.transient(self.root)
        win.grab_set()

        tk.Label(
            win, text="Select the label for this area:", bg=BG_PANEL, fg="black"
        ).pack(pady=(10, 5))

        listbox = tk.Listbox(win, height=10)
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        for c in self.classes:
            listbox.insert("end", c)

        if self.classes:
            listbox.selection_set(0)

        def confirmar():
            sel = listbox.curselection()
            if sel:
                resultado["classe"] = listbox.get(sel[0])
            win.destroy()

        def cancelar():
            resultado["classe"] = None
            win.destroy()

        listbox.bind("<Double-Button-1>", lambda e: confirmar())

        btn_frame = tk.Frame(win, bg=BG_PANEL)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(
            btn_frame, text="Confirm", bg=HIGHLIGHT_COLOR, command=confirmar
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            btn_frame, text="Cancel", bg=BTN_COLOR, command=cancelar
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        win.protocol("WM_DELETE_WINDOW", cancelar)
        btn_frame.bind("<Return>", lambda event: confirmar())
        btn_frame.bind("<Escape>", lambda event: cancelar())
        btn_frame.focus_set()

        self.root.wait_window(win)
        return resultado["classe"]

    # ------------------------------------------------------------------
    # Ajuda / atalhos de teclado
    # ------------------------------------------------------------------
    def show_shortcuts_help(self):
        win = tk.Toplevel(self.root)
        win.title("Keyboard shortcuts")
        win.configure(bg=BG_PANEL)
        win.geometry("380x380")
        win.transient(self.root)

        tk.Label(
            win, text="Keyboard shortcuts", bg=BG_PANEL, fg="black",
            font=("Arial", 12, "bold")
        ).pack(pady=(10, 5))

        atalhos = [
            ("← / →", "Previous / next image"),
            ("S", "Select current image (to move)"),
            ("M", "Move selected images to another folder"),
            ("H", "Image histogram"),
            ("R", "Enable/disable rectangular area selection"),
            ("C", "Enable/disable circular area selection"),
            ("A", "Enable/disable adjust mode (resize an area that has already been created)"),
            ("P", "Jump to a specific image"),
            ("0", "Reset zoom (or double-click the image)"),
            ("Delete", "Delete the highlighted area (click on it first)"),
        ]

        frame = tk.Frame(win, bg=BG_PANEL)
        frame.pack(fill="both", expand=True, padx=15, pady=5)

        for tecla, desc in atalhos:
            row = tk.Frame(frame, bg=BG_PANEL)
            row.pack(fill="x", pady=3)
            tk.Label(
                row, text=tecla, bg="lightblue", fg="black", width=8,
                font=("Arial", 9, "bold")
            ).pack(side="left", padx=(0, 8))
            tk.Label(
                row, text=desc, bg=BG_PANEL, fg="black", anchor="w",
                justify="left", wraplength=240
            ).pack(side="left", fill="x", expand=True)

        tk.Button(win, text="Close", bg=BTN_COLOR, command=win.destroy).pack(pady=10)

    def on_key_press(self, event):
        # Ignora atalhos enquanto o usuário digita em uma caixa de texto
        foco = self.root.focus_get()
        if isinstance(foco, (tk.Entry, tk.Text)):
            return

        tecla = event.keysym or ""
        tecla_lower = tecla.lower()

        if tecla == "Left":
            self.previous_image()
        elif tecla == "Right":
            self.next_image()
        elif tecla in ("Delete", "KP_Delete"):
            self.delete_selected_annotation()
        elif tecla_lower == "s":
            self.toggle_select_current()
        elif tecla_lower == "h":
            self.show_histogram()
        elif tecla_lower == "c":
            self.set_area_mode("ellipse")
        elif tecla_lower == "r":
            self.set_area_mode("rect")
        elif tecla_lower == "a":
            self.toggle_ajustar_mode()
        elif tecla_lower == "p":
            self.jump_to_file()
        elif tecla_lower == "m":
            self.move_selected_images()
        elif tecla == "0":
            self.reset_zoom()


if __name__ == "__main__":
    root = tk.Tk()
    app = ThermalViewer(root)
    root.mainloop()
