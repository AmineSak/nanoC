; --- moule.asm ---
extern printf, atoi, malloc,strlen, strcpy, strcat

section .data
    fmt_int:  db "%ld", 10, 0   ; Use %ld for 64-bit integers
    argv_ptr: dq 0
    
    fmt_str: db "%s", 10, 0
    fmt_char: db "%c",10, 0
    

    DECL_VARS                   ; Placeholder for global variables

section .text
global main

FUNCTIONS                       ; Placeholder for all user-defined functions

; --- Main function entry point ---
main:
    push rbp
    mov rbp, rsp
    sub rsp, 256                ; Reserve stack space for main's local variables
    
    ; Save command line arguments pointer
    mov [argv_ptr], rsi

    INIT_VARS                   ; Placeholder for initializing main's parameters from argv
    
    COMMANDE                    ; Placeholder for main's body
    
    ; Main function epilogue (return value in rax is the exit code)
main_epilogue:
    mov rsp, rbp
    pop rbp
    ret

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
    mov r9, rax             ; pointeur vers nouvelle chaîne

    mov rdi, r9
    mov rsi, [rbp-8]
    call strcpy

    mov rdi, r9
    mov rsi, [rbp-16]
    call strcat

    mov rax, r9

    leave
    ret
