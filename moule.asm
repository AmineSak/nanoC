; moule_or.asm

extern printf, atoi, malloc

section .data
DECL_VARS
argv: dq 0
fmt_int: db "%d", 10, 0

global main
section .text

main:
    push rbp
    mov [argv], rsi

    INIT_VARS

    COMMANDE

    RETOUR
    mov rdi, fmt_int
    mov rsi, rax
    xor rax, rax
    call printf

    pop rbp
    ret
