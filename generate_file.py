sentence = "This is our cute big txt file that we will encrypt.\n"
size_mo=50
size = size_mo * 1024 * 1024  # 500 MB

with open(str(size_mo)+"Mo_file.txt", "w", encoding="utf-8") as f:
    written = 0
    while written < size:
        f.write(sentence)
        written += len(sentence.encode("utf-8"))
print("File generated successfully.")
