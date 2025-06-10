extern printf, atoi, strlen, malloc, strcpy, strcat

section .data
    DECL_VARS
    argv: dq 0
    fmt_int: db "%d", 10, 0
    fmt_str: db "%s", 10, 0
    fmt_char: db "%c",10, 0
    

section .text
    global main

strcat_custom:
    ; rdi = première chaîne, rsi = deuxième chaîne
    ; Retourne l'adresse de la nouvelle chaîne concaténée dans rax
    push rbp
    mov rbp, rsp
    sub rsp, 32             ; espace pour stocker temporairement

    mov [rbp-8], rdi        ; sauvegarder rdi
    mov [rbp-16], rsi       ; sauvegarder rsi

    mov rdi, [rbp-8]        ; strlen première chaîne
    call strlen
    mov r8, rax

    mov rdi, [rbp-16]       ; strlen deuxième chaîne
    call strlen
    add rax, r8
    inc rax                 ; +1 pour '\0'

    mov rdi, rax
    call malloc
    mov r9, rax             ;  un espace mémoire suffisant pour contenir la chaîne concaténée.

    mov rdi, r9
    mov rsi, [rbp-8]
    call strcpy

    mov rdi, r9
    mov rsi, [rbp-16]
    call strcat

    mov rax, r9

    leave
    ret

main:
    push rbp
    mov rbp, rsp
    mov [argv],rsi
    INIT_VARS
    COMMANDE
    
    pop rbp
    ret