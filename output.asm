extern printf, atoi

section .data

x: dq 0
; Function fib is defined in the text section

argv: dq 0
fmt_int: db "%d", 10, 0

section .text
global main


; Function: fib
fib:
    push rbp                ; Save old base pointer
    mov rbp, rsp            ; Set new base pointer
    sub rsp, 128            ; Reserve stack space for local variables
    mov [rbp-8], rdi ; Save parameter 'n' from rdi

    mov rax, [rbp-8]
push rax
mov rax, 1
mov rbx, rax
pop rax
cmp rax, rbx
setle al
movzx rax, al
    cmp rax, 0
    jz endif0
mov rax, [rbp-8]
    jmp fib_epilogue


endif0:
    nop

mov rax, [rbp-8]
push rax
mov rax, 1
mov rbx, rax
pop rax
sub rax, rbx
push rax
pop rdi
call fib

push rax
mov rax, [rbp-8]
push rax
mov rax, 2
mov rbx, rax
pop rax
sub rax, rbx
push rax
pop rdi
call fib

mov rbx, rax
pop rax
add rax, rbx
    jmp fib_epilogue


fib_epilogue:
    mov rsp, rbp
    pop rbp
    ret


main:
    push rbp                ; Save old base pointer
    mov rbp, rsp           ; Set up new base pointer
    sub rsp, 128           ; Reserve space for local variables (aligned to 16 bytes)
    mov [argv], rsi        ; Store argv
    
mov rbx, [argv]
mov rdi, [rbx + 8]
call atoi
mov [x], rax


mov rax, [x]
push rax
pop rdi
call fib

mov [rbp-8], rax  ; local var result
mov rax, [rbp-8]
mov rsi, rax
mov rdi, fmt_int
xor rax, rax
call printf

mov rax, 0
    jmp main_epilogue

main_epilogue:
    mov rsp, rbp
    pop rbp
    ret


