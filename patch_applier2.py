import os
import json
import shutil
import zlib
import tkinter as tk
from tkinter import filedialog, messagebox

def apply_binary_diff(old_bytes, compressed_delta):
    """
    Decompresses the .nexuspatch file and rebuilds the target binary
    by reading the REF offsets and RAW byte injections.
    """
    delta_bytes = zlib.decompress(compressed_delta)
    new_data = bytearray()
    i = 0
    
    while i < len(delta_bytes):
        # Handle Reference Blocks (Unchanged data)
        if delta_bytes[i:i+4] == b"REF:":
            pipe_idx = delta_bytes.find(b"|", i)
            params = delta_bytes[i+4:pipe_idx].decode('utf-8').split(',')
            offset, length = int(params[0]), int(params[1])
            new_data.extend(old_bytes[offset:offset+length])
            i = pipe_idx + 1
            
        # Handle Raw Blocks (New/Modified data)
        elif delta_bytes[i:i+4] == b"RAW:":
            pipe_idx = i + 4
            # Scan forward to find the terminating pipe delimiter safely
            while pipe_idx < len(delta_bytes):
                pipe_idx = delta_bytes.find(b"|", pipe_idx)
                if pipe_idx == -1:
                    pipe_idx = len(delta_bytes)
                    break
                # Ensure the pipe is an actual delimiter, not a raw byte value
                if pipe_idx == len(delta_bytes) - 1 or delta_bytes[pipe_idx+1:pipe_idx+5] in (b"REF:", b"RAW:"):
                    break
                pipe_idx += 1
            
            new_data.extend(delta_bytes[i+4:pipe_idx])
            i = pipe_idx + 1
        else:
            break
            
    return new_data

def apply_patch():
    game_dir = filedialog.askdirectory(title="1. Select Your Game Folder (To be updated)")
    if not game_dir: return
    
    patch_dir = filedialog.askdirectory(title="2. Select The Patch Package Folder")
    if not patch_dir: return
    
    manifest_path = os.path.join(patch_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        messagebox.showerror("Error", "Invalid patch folder. manifest.json not found.")
        return
        
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            
        # 1. Inject completely new files
        for rel_path in manifest.get("added", []):
            src_file = os.path.join(patch_dir, rel_path)
            dest_file = os.path.join(game_dir, rel_path)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            shutil.copy2(src_file, dest_file)
            
        # 2. Reconstruct binary files using .nexuspatch micro-deltas
        for rel_path in manifest.get("modified_deltas", []):
            old_file_path = os.path.join(game_dir, rel_path)
            patch_file_path = os.path.join(patch_dir, rel_path + ".nexuspatch")
            
            with open(old_file_path, 'rb') as f:
                old_bytes = f.read()
            with open(patch_file_path, 'rb') as f:
                compressed_delta = f.read()
                
            new_bytes = apply_binary_diff(old_bytes, compressed_delta)
            
            with open(old_file_path, 'wb') as f:
                f.write(new_bytes)
                
        # 3. Purge deleted files
        for rel_path in manifest.get("deleted", []):
            target_file = os.path.join(game_dir, rel_path)
            if os.path.exists(target_file):
                os.remove(target_file)
                
        messagebox.showinfo("Update Complete", "Game successfully updated via NEXUS Pipeline!")
        
    except Exception as e:
        messagebox.showerror("Update Failed", f"An error occurred while patching:\n{str(e)}")

app = tk.Tk()
app.title("NEXUS Consumer Applier")
app.geometry("350x150")
app.eval('tk::PlaceWindow . center')

tk.Button(app, text="Apply NEXUS Update", command=apply_patch, bg="green", fg="white", font=("Arial", 11, "bold")).pack(pady=40)

app.mainloop()