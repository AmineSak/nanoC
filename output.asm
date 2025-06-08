; moule_or.asm

extern printf, atoi, malloc

section .data
x: dq 0
y: dq 0
b: dq 0
tab: dq 0
i: dq 0
a: dq 0

argv: dq 0
fmt_int: db "%d", 10, 0

global main
section .text

main:
    push rbp
    mov [argv], rsi

    mov rbx, [argv]
mov rdi, [rbx + 8]
call atoi
mov [x], rax
mov rbx, [argv]
mov rdi, [rbx + 16]
call atoi
mov [y], rax


    mov rax, 10
mov rdi, rax
shl rdi, 3
call malloc
mov [tab], rax
mov rax, 1
mov rbx, [tab]
mov [rbx + 0], rax
mov rax, 2
mov rbx, [tab]
mov [rbx + 8], rax
mov rax, 3
mov rbx, [tab]
mov [rbx + 16], rax
mov rax, 4
mov rbx, [tab]
mov [rbx + 24], rax
mov rax, 5
mov rbx, [tab]
mov [rbx + 32], rax
mov rax, 6
mov rbx, [tab]
mov [rbx + 40], rax
mov rax, 7
mov rbx, [tab]
mov [rbx + 48], rax
mov rax, 8
mov rbx, [tab]
mov [rbx + 56], rax
mov rax, 9
mov rbx, [tab]
mov [rbx + 64], rax
mov rax, 10
mov rbx, [tab]
mov [rbx + 72], rax

mov rax, 0
mov [i], rax
loop0: mov rax, [i]
push rax
mov rax, 10
mov rbx, rax
pop rax
cmp rax, rbx
setl al
movzx rax, al
cmp rax, 0
jz end0
mov rax, [i]
mov rcx, rax
shl rcx, 3
mov rbx, [tab]
mov rax, [rbx + rcx]
mov [a], rax
mov rax, [a]
push rax
mov rax, 10
mov rbx, rax
pop rax
add rax, rbx
mov [b], rax
mov rax, [b]
mov rsi, rax
mov rdi, fmt_int
xor rax, rax
call printf

mov rax, [i]
add rax, 1
mov [i], rax
jmp loop0
end0: nop

    mov rax, [x]
    mov rdi, fmt_int
    mov rsi, rax
    xor rax, rax
    call printf

    pop rbp
    ret
