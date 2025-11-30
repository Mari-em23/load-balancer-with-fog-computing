# Génération d'un fichier texte de grande taille
sentence = "This is our cute big txt file that we will encrypt.\n"
size_mo = 20  # taille du fichier en Mo
size = size_mo * 1024 * 1024  # conversion en octets

filename = f"{size_mo}Mo_file.txt"

with open(filename, "w", encoding="utf-8") as f:
    written = 0
    while written < size:
        f.write(sentence)
        written += len(sentence.encode("utf-8"))

print(f"File '{filename}' generated successfully ({size_mo} Mo).")
