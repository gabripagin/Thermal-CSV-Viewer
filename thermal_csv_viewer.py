
# thermal_csv_viewer.py
# Thermal CSV Analyzer
# Requer: pip install pandas numpy matplotlib pillow
# Gerar Executável:
# python -m PyInstaller --onefile --windowed --clean --icon=logo.ico --add-data "logo2.png;." --add-data "logo.ico;." thermal_csv_viewer.py

import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import RectangleSelector
import matplotlib.pyplot as plt
from PIL import Image, ImageTk

def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS

    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

BG_MAIN = "#173f4f"      
BG_PANEL = "#173f4f"     
BTN_COLOR = "#E9A03B"    
BTN_HOVER = "#FFB000"    

class ThermalViewer:

    def __init__(self, root):
        self.root = root
        
        try:
            self.root.iconbitmap(
                resource_path("logo.ico")
            )
        except:
            pass
        
        self.root.title("Thermal CSV Viewer  v2.0")
        self.root.geometry("900x830")
        self.root.minsize(900, 780)
        self.root.resizable(False, False)
        self.root.configure(bg=BG_MAIN)

        self.csv_files = []
        self.current_index = 0
        self.current_data = None
        self.colorbar = None

        # --- Seleção de imagens para mover ---
        self.selected_files = set()

        # --- Seleção de área (média/min/max) ---
        self.area_select_active = False
        self.rect_selector = None

        self.build_gui()

    def build_gui(self):

        top = tk.Frame(self.root, bg=BG_MAIN)
        top.pack(fill="x", pady=5)

        # Caminho do logo
        logo_path = "logo2.png"

        try:

            logo_img = Image.open(resource_path(logo_path))
            logo_img = logo_img.resize((60, 60))

            self.logo_tk = ImageTk.PhotoImage(logo_img)

            self.logo = tk.Label(
                top,
                image=self.logo_tk,
                bg=BG_MAIN
            )

        except:

            self.logo = tk.Label(
                top,
                text="LOGO",
                bg="white",
                width=15
            )

        self.logo.pack(side="left", padx=10)


        title = tk.Label(
                    top,
                    text="Thermal CSV Viewer",
                    font=("Arial", 15, "bold"),
                    bg=BG_MAIN,
                    fg="white"
                )
        title.pack(side="left", padx=60)


        copyright_label = tk.Label(
            top,
            text="© Gabriel Pagin 2026",
            bg=BG_MAIN,
            fg="#D0D0D0",
            font=("Segoe UI", 7)
        )

        copyright_label.pack(side="right", padx=20)
    
        main = tk.Frame(self.root, bg=BG_MAIN)
        main.pack(fill="both", expand=True, pady=12, padx=15)

        left = tk.Frame(
            main,
            bg=BG_PANEL
        )

        left.pack(
            side="left",
            fill="both",
            expand=False
        )

        self.filename_label = tk.Label(
            left,
            text="No file uploaded",
            bg=BG_PANEL,
            fg="white",
            font=("Arial", 12, "bold")
        )
        self.filename_label.pack()

        self.fig = Figure(figsize=(5, 4), facecolor=BG_PANEL)
        self.ax = self.fig.add_subplot(111)
        
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
            bg="#8b9fa7",
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
            #expand=True,
            padx=3,
            pady=3
        )

        self.canvas.mpl_connect("motion_notify_event", self.mouse_move)
        self.canvas.mpl_connect("scroll_event", self.zoom)

        nav = tk.Frame(left, bg=BG_PANEL)
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

        move_frame = tk.Frame(left, bg=BG_PANEL)
        move_frame.pack(fill="x", pady=5)

        self.selected_label = tk.Label(
            move_frame,
            text="Selected images: 0",
            bg=BG_PANEL,
            fg="white"
        )
        self.selected_label.pack(side="left", padx=5)

        self.move_btn = tk.Button(
            move_frame,
            text="Move selected images",
            bg=BTN_COLOR,
            state="disabled",
            command=self.move_selected_images
        )
        self.move_btn.pack(side="left", padx=5, fill="x", expand=True)

        self.status = tk.Label(
            left,
            text="X=- Y=- Temp=-",
            bg="#8b9fa7",
            fg="white",
            anchor="w"
        )
        self.status.pack(fill="x")

        right = tk.Frame(
            main,
            width=180,
            bg=BG_PANEL
        )

        right.pack(
            side="left",
            fill="y",
            padx=10,
            pady=10
        )

        right.pack_propagate(False)

        tk.Button(
            right,
            text="Select Folder",
            bg=BTN_COLOR,
            command=self.select_folder
        ).pack(fill="x", pady=5)

        tk.Button(
            right,
            text="Search for image",
            bg=BTN_COLOR,
            command=self.jump_to_file
        ).pack(fill="x", pady=5)

        self.min_label = tk.Label(right, text="Min:", bg=BG_PANEL, fg="white")
        self.min_label.pack(anchor="w")

        self.max_label = tk.Label(right, text="Max:", bg=BG_PANEL, fg="white")
        self.max_label.pack(anchor="w")

        self.mean_label = tk.Label(right, text="Mean:", bg=BG_PANEL, fg="white")
        self.mean_label.pack(anchor="w")

        self.std_label = tk.Label(right, text="Standard deviation:", bg=BG_PANEL, fg="white")
        self.std_label.pack(anchor="w")

        tk.Label(right, text="Minimum scale", bg=BG_PANEL, fg="white").pack(anchor="w")
        self.vmin_entry = tk.Entry(right)
        self.vmin_entry.pack(fill="x")

        tk.Label(right, text="Maximum scale", bg=BG_PANEL, fg="white").pack(anchor="w")
        self.vmax_entry = tk.Entry(right)
        self.vmax_entry.pack(fill="x")

        tk.Button(right, text="Apply Scale", bg=BTN_COLOR,
                  command=self.show_image).pack(fill="x", pady=5)

        tk.Label(right, text="Palette", bg=BG_PANEL, fg="white").pack(anchor="w")

        self.cmap = ttk.Combobox(
            right,
            state="readonly",
            values=["turbo","inferno","magma","plasma","viridis","jet","hot","coolwarm","gray","gray_r"]
        )
        self.cmap.set("turbo")
        self.cmap.pack(fill="x")
        self.cmap.bind("<<ComboboxSelected>>", lambda e: self.show_image())

        self.area_btn = tk.Button(
            right,
            text="Select Area",
            bg=BTN_COLOR,
            command=self.toggle_area_select
        )
        self.area_btn.pack(fill="x", pady=2)

        self.area_label = tk.Label(
            right,
            text="Area: -",
            bg=BG_PANEL,
            fg="white",
            wraplength=140,
            justify="left"
        )
        self.area_label.pack(anchor="w", pady=5)

        tk.Button(right, text="Histogram", bg=BTN_COLOR,
                  command=self.show_histogram).pack(fill="x", pady=2)

        tk.Button(right, text="Save PNG", bg=BTN_COLOR,
                  command=self.save_png).pack(fill="x", pady=2)

        tk.Button(right, text="Save JPG", bg=BTN_COLOR,
                  command=self.save_jpg).pack(fill="x", pady=2)
        
    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.csv_files = sorted([
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(".csv")
        ])

        if not self.csv_files:
            messagebox.showerror("Error", "No CSV found.")
            return

        self.current_index = 0
        self.selected_files = set()
        self.area_select_active = False
        self.area_btn.config(text="Select Area", bg=BTN_COLOR)
        self.area_label.config(text="Area: -")
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

        self.rect_selector = None
        self.canvas.draw()
    
    def load_current(self):

        file = self.csv_files[self.current_index]

        self.filename_label.config(
            text=os.path.basename(file)
        )

        self.area_label.config(text="Area: -")
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
                text=f"Mean: {np.nanmean(self.current_data):.2f} °C"
            )

            self.std_label.config(
                text=f"Standard deviation: {np.nanstd(self.current_data):.2f}"
            )

            self.show_image()

        except Exception as e:

            print(
                f"Error opening {file}: {e}"
            )

            self.current_data = None

            self.min_label.config(text="Min: -")
            self.max_label.config(text="Max: -")
            self.mean_label.config(text="Mean: -")
            self.std_label.config(text="Standar deviation: -")

            self.show_error_image()

    def show_image(self):
        if self.current_data is None:
            return

        self.fig.clear()

        self.ax = self.fig.add_subplot(111)
        
        try:
            vmin = float(self.vmin_entry.get())
            vmax = float(self.vmax_entry.get())
        except:
            vmin = np.min(self.current_data)
            vmax = np.max(self.current_data)

        img = self.ax.imshow(
            self.current_data,
            cmap=self.cmap.get(),
            vmin=vmin,
            vmax=vmax
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
        
       # if self.colorbar:
       #     self.colorbar.remove()

        self.colorbar = self.fig.colorbar(img, ax=self.ax)
        self.canvas.draw()

        if self.area_select_active:
            self.enable_rect_selector()

    def mouse_move(self, event):

        if self.current_data is None:
            return

        if event.xdata is None or event.ydata is None:
            return

        x = int(event.xdata)
        y = int(event.ydata)

        try:

            temp = self.current_data[y, x]

            self.status.config(
                text=f"X={x}  Y={y}  Temp={temp:.2f} °C"
            )

            self.temp_text.set_position(
                (x, y)
            )

            self.temp_text.set_text(
                f"{temp:.2f}°C"
            )

            self.canvas.draw_idle()
            self.hline.set_ydata([y])
            self.vline.set_xdata([x])

        except Exception as e:
            print(e)

    def zoom(self, event):
        if event.xdata is None:
            return
        scale = 1/1.2 if event.button == "up" else 1.2
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        x = event.xdata
        y = event.ydata

        width = (xlim[1]-xlim[0]) * scale
        height = (ylim[1]-ylim[0]) * scale

        self.ax.set_xlim([x-width/2, x+width/2])
        self.ax.set_ylim([y+height/2, y-height/2])
        self.canvas.draw()

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

    def save_jpg(self):
        file = filedialog.asksaveasfilename(defaultextension=".jpg")
        if file:
            self.fig.savefig(file, dpi=300)

    def show_histogram(self):
        if self.current_data is None:
            return
        plt.figure()
        plt.hist(self.current_data.ravel(), bins=50)
        plt.xlabel("Temperature")
        plt.ylabel("Frequence")
        plt.title("Thermal Histogram")
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
                self.select_btn.config(text="✔ Selected", bg="#2ECC71")
            else:
                self.select_btn.config(text="Select", bg=BTN_COLOR)

    def move_selected_images(self):
        if not self.selected_files:
            return

        dest = filedialog.askdirectory(
            title="Select the destination folder (use 'New Folder' to create one)"
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
                f"{len(moved)} file(s) moved(s) to:\n{dest}"
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
            messagebox.showwarning("Warning", "No folder loaded")
            return

        nome = simpledialog.askstring(
            "Skip to",
            "Enter the CSV file name (or part of it):",
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
            f"No files found with'{nome}'."
        )

    # ------------------------------------------------------------------
    # Seleção de área (média / min / max)
    # ------------------------------------------------------------------
    def toggle_area_select(self):
        self.area_select_active = not self.area_select_active

        if self.area_select_active:
            self.area_btn.config(text="Select Area (active)", bg="#2ECC71")
            self.enable_rect_selector()
        else:
            self.area_btn.config(text="Select Area", bg=BTN_COLOR)
            self.disable_rect_selector()

    def enable_rect_selector(self):
        if self.current_data is None:
            return

        self.rect_selector = RectangleSelector(
            self.ax,
            self.on_area_select,
            useblit=True,
            button=[1],
            minspanx=1,
            minspany=1,
            spancoords="data",
            interactive=True
        )

    def disable_rect_selector(self):
        if self.rect_selector is not None:
            try:
                self.rect_selector.set_active(False)
            except Exception:
                pass
            self.rect_selector = None

        self.canvas.draw_idle()

    def on_area_select(self, eclick, erelease):
        if self.current_data is None:
            return

        if eclick.xdata is None or erelease.xdata is None:
            return
        if eclick.ydata is None or erelease.ydata is None:
            return

        x0, x1 = sorted([eclick.xdata, erelease.xdata])
        y0, y1 = sorted([eclick.ydata, erelease.ydata])

        h, w = self.current_data.shape

        xi0 = max(0, int(round(x0)))
        xi1 = min(w - 1, int(round(x1)))
        yi0 = max(0, int(round(y0)))
        yi1 = min(h - 1, int(round(y1)))

        if xi1 < xi0 or yi1 < yi0:
            return

        regiao = self.current_data[yi0:yi1 + 1, xi0:xi1 + 1]

        if regiao.size == 0:
            return

        media = np.nanmean(regiao)
        minimo = np.nanmin(regiao)
        maximo = np.nanmax(regiao)

        self.area_label.config(
            text=(
                f"Area ({xi0},{yi0}) a ({xi1},{yi1})\n"
                f"Mean: {media:.2f} °C\n"
                f"Min: {minimo:.2f} °C\n"
                f"Max: {maximo:.2f} °C"
            )
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = ThermalViewer(root)
    root.mainloop()
