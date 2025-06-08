extern printf, atoi

section .data

DECL_VARS
argv: dq 0
fmt_int: db "%d", 10, 0

section .text
global main

FUNCTIONS

main:
    push rbp                ; Save old base pointer
    mov rbp, rsp           ; Set up new base pointer
    sub rsp, 128           ; Reserve space for local variables (aligned to 16 bytes)
    mov [argv], rsi        ; Store argv
    
INIT_VARS

COMMANDE

