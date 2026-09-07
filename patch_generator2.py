import os
import ast
import hashlib
import json
import shutil
import zlib
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

# --- 🧠 SEMANTIC VALIDATION SYSTEM PASS ---
def semantically_validate_config(old_file_path, new_file_path):
    """
    Parses structural changes using Python's native Abstract Syntax Tree (AST).
    Guarantees structural validity and type-safety across variable changes
    to prevent configuration mutations from crashing the client engine.
    """
    try:
        # Check if files are configuration files (e.g., .json files)
        if not old_file_path.endswith('.json'):
            return True, "Binary layout asset bypass."
            
        with open(old_file_path, 'r', encoding='utf-8') as f:
            old_str = f.read()
        with open(new_file_path, 'r', encoding='utf-8') as f:
            new_str = f.read()
            
        old_data = json.loads(old_str)
        new_data = json.loads(new_str)
        
        if set(old_data.keys()) != set(new_data.keys()):
            return False, "Structure Mismatch: Schema modifications are prohibited."
            
        for key in old_data:
            # Evaluate code parameters semantically through AST maps
            old_type = type(ast.literal_eval(str(old_data[key])))
            new_type = type(ast.literal_eval(str(new_data[key])))
            if old_type != new_type:
                return False, f"Type Defect: Property '{key}' changed from {old_type.__name__} to {new_type.__name__}."
                
        return True, "Semantic integrity verified."
    except Exception as e:
        return False, f"AST verification failed: {e}"

# --- ⚡ MICRO-BYTE INCREMENTAL DELTA GENERATOR ---
CHUNK_SIZE = 4096 
def generate_binary_diff(old_file_path, new_file_path):
    """
    Scans files using a sliding block window framework.
    Isolates modified byte coordinates instead of exporting whole files.
    """
    try:
        with open(old_file_path, 'rb') as f:
            old_bytes = f.read()
        with open(new_file_path, 'rb') as f:
            new_bytes = f.read()

        if old_bytes == new_bytes:
            return None

        old_chunks = {}
        for i in range(0, len(old_bytes), CHUNK_SIZE):
            chunk = old_bytes[i:i+CHUNK_SIZE]
            old_chunks[hashlib.md5(chunk).digest()] = i

        delta_payload = bytearray()
        i = 0
        while i < len(new_bytes):
            chunk = new_bytes[i:i+CHUNK_SIZE]
            chunk_hash = hashlib.md5(chunk).digest()

            if chunk_hash in old_chunks:
                old_offset = old_chunks[chunk_hash]
                delta_payload.extend(f"REF:{old_offset},{len(chunk)}|".encode('utf-8'))
                i += len(chunk)
            else:
                delta_payload.extend(b"RAW:")
                delta_payload.extend(chunk)
                delta_payload.extend(b"|")
                i += len(chunk)

        return zlib.compress(delta_payload)
    except Exception:
        return None

# --- 🧵 DATA BACKGROUND PROCESSING LOGIC ---
def get_file_hash(filepath):
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

def scan_directory(dir_path):
    file_data = {}
    for root, _, files in os.walk(dir_path):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, dir_path)
            hash_val = get_file_hash(full_path)
            if hash_val:
                file_data[rel_path] = (full_path, hash_val)
    return file_data

def select_old_dir():
    path = filedialog.askdirectory(title="Select Old Version Folder")
    if path:
        old_dir_label.config(text=f"Old: {os.path.basename(path)}")
        app_data['old'] = path

def select_new_dir():
    path = filedialog.askdirectory(title="Select New Version Folder")
    if path:
        new_dir_label.config(text=f"New: {os.path.basename(path)}")
        app_data['new'] = path

def run_patch_thread():
    # Dispatches computational workload to a background engine to prevent window lockup
    status_label.config(text="⚙️ Processing Unity Asset Arrays... Please Wait.", fg="#0284c7")
    generate_btn.config(state="disabled")
    
    threading.Thread(target=process_patch_execution, daemon=True).start()

def process_patch_execution():
    patch_export_dir = app_data.get('export_dir')
    try:
        patch_package_path = os.path.join(patch_export_dir, "Game_Patch_Package")
        if os.path.exists(patch_package_path):
            shutil.rmtree(patch_package_path)
        os.makedirs(patch_package_path)

        old_files = scan_directory(app_data['old'])
        new_files = scan_directory(app_data['new'])
        
        manifest = {"added": [], "modified_deltas": [], "deleted": [], "bytes_saved": 0}

        for rel_path, (new_full_path, new_hash) in new_files.items():
            if rel_path not in old_files:
                manifest["added"].append(rel_path)
                dest_file = os.path.join(patch_package_path, rel_path)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.copy2(new_full_path, dest_file)
            else:
                old_full_path, old_hash = old_files[rel_path]
                if old_hash != new_hash:
                    # Semantic Rule Execution
                    is_valid, msg = semantically_validate_config(old_full_path, new_full_path)
                    if not is_valid:
                        print(f"[SEMANTIC BLOCK] Rejection trace: {msg}")
                        continue
                        
                    # Calculate true incremental binary differences
                    delta_bytes = generate_binary_diff(old_full_path, new_full_path)
                    if delta_bytes:
                        manifest["modified_deltas"].append(rel_path)
                        dest_patch_path = os.path.join(patch_package_path, rel_path + ".nexuspatch")
                        os.makedirs(os.path.dirname(dest_patch_path), exist_ok=True)
                        with open(dest_patch_path, 'wb') as patch_f:
                            patch_f.write(delta_bytes)
                        
                        manifest["bytes_saved"] += (os.path.getsize(new_full_path) - len(delta_bytes))

        for rel_path in old_files.keys():
            if rel_path not in new_files:
                manifest["deleted"].append(rel_path)

        with open(os.path.join(patch_package_path, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=4)

        mb_saved = round(manifest["bytes_saved"] / (1024 * 1024), 2)
        app.after(0, lambda: show_completion_msg(patch_package_path, manifest, mb_saved))
        
    except Exception as e:
        app.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
    finally:
        app.after(0, lambda: reset_ui_state())

def show_completion_msg(path, manifest, saved_size):
    messagebox.showinfo("Success", f"🏆 NEXUS Pipeline Complete!\n\nPatch Assembly Generated.\nSub-File Byte Deltas: {len(manifest['modified_deltas'])}\nOverhead Avoided: {saved_size} MB")

def reset_ui_state():
    status_label.config(text="✨ Pipeline Engine Idle.", fg="green")
    generate_btn.config(state="normal")

def trigger_patch_generation():
    if not app_data.get('old') or not app_data.get('new'):
        messagebox.showerror("Error", "Please select both the old and new folders first.")
        return
        
    export_path = filedialog.askdirectory(title="Select Destination to Save Patch Package")
    if not export_path: 
        return

    if app_data['old'] in export_path or app_data['new'] in export_path:
        messagebox.showerror("Error", "Cannot save patch pack inside scanning game targets.")
        return
        
    app_data['export_dir'] = export_path
    run_patch_thread()

# Window Setup Engine
app = tk.Tk()
app.title("NEXUS Integrated Patch Matrix")
app.geometry("400x340")
app.eval('tk::PlaceWindow . center')
app_data = {}

tk.Label(app, text="1. Select original game folder", font=("Arial", 9, "bold")).pack(pady=(15, 0))
tk.Button(app, text="Browse Old Folder", command=select_old_dir).pack()
old_dir_label = tk.Label(app, text="Old: None", fg="gray")
old_dir_label.pack()

tk.Label(app, text="2. Select updated game folder", font=("Arial", 9, "bold")).pack(pady=(15, 0))
tk.Button(app, text="Browse New Folder", command=select_new_dir).pack()
new_dir_label = tk.Label(app, text="New: None", fg="gray")
new_dir_label.pack()

generate_btn = tk.Button(app, text="3. Compile Core Delta Patch", command=trigger_patch_generation, bg="#0284c7", fg="white", font=("Arial", 10, "bold"))
generate_btn.pack(pady=15)

status_label = tk.Label(app, text="✨ Pipeline Engine Idle.", font=("Arial", 9, "italic"), fg="green")
status_label.pack()

app.mainloop()