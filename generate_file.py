sentence = "This is our cute big txt file that we will encrypt.\n"
size_mo = 2000
size_bytes = size_mo * 1024 * 1024

repeats = size_bytes // len(sentence.encode("utf-8"))

with open(f"{size_mo}Mo_file.txt", "w", encoding="utf-8") as f:
    for _ in range(repeats):
        f.write(sentence)

print("File generated successfully")
