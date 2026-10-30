"""Turn an MPMB character sheet into a plain fillable template for the builder.

Removes the document scripts, field scripts and calculation order, hides MPMB's on-screen control
buttons, and turns rich-text fields into plain ones (the browser fill library can't handle rich text).
The page design is untouched.

    python3 tools/clean_sheet.py "MPMB's Character Record Sheet ... .pdf" character-sheet-template.pdf
"""
import sys

import pikepdf

src, dst = sys.argv[1], sys.argv[2]
pdf = pikepdf.open(src)
root = pdf.Root
if "/Names" in root and "/JavaScript" in root.Names:
    del root.Names["/JavaScript"]
for k in ("/AA", "/OpenAction"):
    if k in root:
        del root[k]
if "/CO" in root.AcroForm:
    del root.AcroForm["/CO"]
c = {"aa": 0, "js": 0, "buttons": 0, "richtext": 0}
for o in pdf.objects:
    if not isinstance(o, pikepdf.Dictionary):
        continue
    if "/AA" in o:
        del o["/AA"]; c["aa"] += 1
    if "/A" in o and isinstance(o.A, pikepdf.Dictionary) and o.A.get("/S") == "/JavaScript":
        del o["/A"]; c["js"] += 1
    if "/RV" in o:
        del o["/RV"]
    if "/Ff" in o and int(o.Ff) & (1 << 25):
        o.Ff = int(o.Ff) & ~(1 << 25); c["richtext"] += 1
    if o.get("/Subtype") == "/Widget":
        par = o.get("/Parent", {})
        ft = o.get("/FT", par.get("/FT")); ff = int(o.get("/Ff", par.get("/Ff", 0)))
        if ft == "/Btn" and ff & 65536:
            o.F = int(o.get("/F", 0)) | 2; c["buttons"] += 1
print(c)
pdf.remove_unreferenced_resources()
pdf.save(dst, compress_streams=True, recompress_flate=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
