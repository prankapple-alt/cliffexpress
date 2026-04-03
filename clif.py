import os
import random
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Temporary folder for chunks
SAVE_FOLDER = "cliffiles"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# ---------------- File Operations ----------------
class FileHandler:

    @staticmethod
    def read_folder(folder: str):
        """Read all files recursively and return (rel_path, data) list."""
        file_data_list = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, start=folder)
                with open(full_path, "rb") as f:
                    file_data_list.append((rel_path, f.read()))
        return file_data_list

    @staticmethod
    def split_file_by_size(data: bytes, chunk_size: int = 1024):
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    @staticmethod
    def save_chunks(file_data_list, corruptfilter: float = 0.0):
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        chunk_counter = 1
        chunk_map = []
        for rel_path, data in file_data_list:
            chunks = FileHandler.split_file_by_size(data)
            for chunk in chunks:
                chunk_filename = f"chunk{chunk_counter:06}.clif"
                chunk_counter += 1
                chunk_map.append((chunk_filename, rel_path))
                chunk_to_save = bytearray(chunk)
                if corruptfilter > 0:
                    for i in range(len(chunk_to_save)):
                        if random.random() < corruptfilter:
                            chunk_to_save[i] = random.randint(0, 255)
                with open(os.path.join(SAVE_FOLDER, chunk_filename), "wb") as f:
                    f.write(chunk_to_save)
        # Save filemap
        with open(os.path.join(SAVE_FOLDER, "filemap.txt"), "w", encoding="utf-8") as f:
            for chunk_filename, rel_path in chunk_map:
                f.write(f"{chunk_filename}|{rel_path}\n")

    @staticmethod
    def zip_chunks(output_zip: str):
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in sorted(os.listdir(SAVE_FOLDER)):
                zipf.write(os.path.join(SAVE_FOLDER, file), arcname=file)

    @staticmethod
    def unzip_eclif(eclif_file: str):
        with zipfile.ZipFile(eclif_file, 'r') as zipf:
            zipf.extractall(SAVE_FOLDER)

    @staticmethod
    def restore_folder(output_folder: str):
        filemap_path = os.path.join(SAVE_FOLDER, "filemap.txt")
        if not os.path.exists(filemap_path):
            raise FileNotFoundError("filemap.txt not found in extracted chunks!")

        chunk_map = []
        with open(filemap_path, "r", encoding="utf-8") as f:
            for line in f:
                chunk_filename, rel_path = line.strip().split("|")
                chunk_map.append((chunk_filename, rel_path))

        file_buffers = {}
        for chunk_filename, rel_path in chunk_map:
            with open(os.path.join(SAVE_FOLDER, chunk_filename), "rb") as f:
                data = f.read()
            if rel_path not in file_buffers:
                file_buffers[rel_path] = bytearray()
            file_buffers[rel_path] += data

        for rel_path, data in file_buffers.items():
            full_path = os.path.join(output_folder, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(data)


# ---------------- GUI ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clif Express")
        self.geometry("500x500")

        # --- Split Frame ---
        ttk.Label(self, text="Folder → .eclif", font=("Arial", 12, "bold")).pack(pady=5)

        self.split_folder_var = tk.StringVar()
        tk.Entry(self, textvariable=self.split_folder_var, width=50).pack(pady=2)
        tk.Button(self, text="Select Folder", command=self.select_split_folder).pack()

        self.chunk_size_var = tk.IntVar(value=1024)
        tk.Label(self, text="Chunk size (bytes):").pack()
        tk.Entry(self, textvariable=self.chunk_size_var).pack()

        self.corrupt_var = tk.DoubleVar(value=0.0)
        tk.Label(self, text="Corruption fraction (0-1):").pack()
        tk.Entry(self, textvariable=self.corrupt_var).pack()

        self.output_zip_var = tk.StringVar(value="files.eclif")
        tk.Label(self, text="Output .eclif filename:").pack()
        tk.Entry(self, textvariable=self.output_zip_var).pack()
        tk.Button(self, text="Split & Zip", command=self.split_folder).pack(pady=5)

        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=10)

        # --- Restore Frame ---
        ttk.Label(self, text="Restore .eclif → Folder", font=("Arial", 12, "bold")).pack(pady=5)

        self.eclif_file_var = tk.StringVar()
        tk.Entry(self, textvariable=self.eclif_file_var, width=50).pack(pady=2)
        tk.Button(self, text="Select .eclif File", command=self.select_eclif_file).pack()

        self.restore_folder_var = tk.StringVar(value="restored_folder")
        tk.Label(self, text="Output folder:").pack()
        tk.Entry(self, textvariable=self.restore_folder_var).pack()
        tk.Button(self, text="Restore Folder", command=self.restore_folder).pack(pady=5)

    # --- Button callbacks ---
    def select_split_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.split_folder_var.set(folder)

    def select_eclif_file(self):
        file = filedialog.askopenfilename(filetypes=[("ECLIF files", "*.eclif")])
        if file:
            self.eclif_file_var.set(file)

    def split_folder(self):
        folder = self.split_folder_var.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Invalid folder selected!")
            return
        chunk_size = self.chunk_size_var.get()
        corruptfilter = self.corrupt_var.get()
        output = self.output_zip_var.get()
        try:
            data_list = FileHandler.read_folder(folder)
            FileHandler.save_chunks(data_list, corruptfilter)
            FileHandler.zip_chunks(output)
            messagebox.showinfo("Success", f"Folder split and zipped to '{output}'")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def restore_folder(self):
        eclif_file = self.eclif_file_var.get()
        output_folder = self.restore_folder_var.get()
        if not os.path.isfile(eclif_file):
            messagebox.showerror("Error", "Invalid .eclif file selected!")
            return
        try:
            FileHandler.unzip_eclif(eclif_file)
            FileHandler.restore_folder(output_folder)
            messagebox.showinfo("Success", f"Folder restored to '{output_folder}'")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()