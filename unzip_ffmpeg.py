import sys, os, zipfile, shutil

zip_name = sys.argv[1] if len(sys.argv) > 1 else "ffmpeg-bundle.zip"
dest = sys.argv[2] if len(sys.argv) > 2 else os.path.join(".", "ffmpeg")

if not os.path.exists(zip_name):
    print(f"❌ Zip not found: {zip_name}")
    raise SystemExit(1)

if os.path.exists(dest):
    shutil.rmtree(dest)
os.makedirs(dest, exist_ok=True)

print(f"Extracting '{zip_name}' -> '{dest}' ...")
with zipfile.ZipFile(zip_name, "r") as z:
    z.extractall(dest)
print("✅ Extracted.")

# Try to locate ffmpeg(.exe)
ff = None
for root, _, files in os.walk(dest):
    for f in files:
        if f.lower() in ("ffmpeg.exe", "ffmpeg"):
            ff = os.path.join(root, f)
            break
    if ff:
        break

if ff:
    ff_dir = os.path.dirname(ff)
    print(f"✅ Found ffmpeg at: {ff}")
    print("For this shell session on Windows PowerShell:")
    print(f'$env:FFMPEG_PATH = "{ff_dir}"')
    print('$env:PATH = "$env:FFMPEG_PATH;$env:PATH"')
else:
    print("⚠️ Could not automatically find ffmpeg in the extracted folder. Check the structure.")
