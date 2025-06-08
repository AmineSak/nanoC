#!/usr/bin/env bash
set -euo pipefail

# 1) Generate assembly

python3 nanoc.py

# 2) Assemble to object file
nasm -f elf64 output.asm

# 3) Link into an executable
gcc -no-pie output.o -o output

# 4) Run it, forwarding any arguments
./output "$@"
