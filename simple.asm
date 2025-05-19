extern printf, atoi

section .data
y: db 0
x: dq 0

argv: dq 0
fmt_int: db "%d", 10, 0

global main
section .text

main:
push rbp
mov [argv],rsi

mov rbx, [argv]
mov rdi, [rbx + 16]
call atoi
mov [x], rax


mov rax, 2
mov [x], rax
mov rax, [x] 
push rax
mov rax, 1
mov rbx, rax
pop rax
sub rax, rbx
mov [x], rax


mov rax, [x]
mov rdi, fmt_int
mov rsi, rax
xor rax, rax
call printf

pop rbp
ret

