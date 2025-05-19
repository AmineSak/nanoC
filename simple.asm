extern printf, atoi

section .data
<<<<<<< HEAD

y: dq 0
x: dq 0

argv: dq 0
fmt_int:db "%d", 10, 0
=======
y: db 0
x: dq 0

argv: dq 0
fmt_int: db "%d", 10, 0
>>>>>>> origin/typage

global main
section .text

main:
push rbp
<<<<<<< HEAD
mov [argv], rsi

mov rbx, [argv]
mov rdi, [rbx + 8]
call atoi
mov [y], rax
mov rbx, [argv]
=======
mov [argv],rsi

mov rbx, [argv]
>>>>>>> origin/typage
mov rdi, [rbx + 16]
call atoi
mov [x], rax

<<<<<<< HEAD
loop0:mov rax, [x]
cmp rax, 0
jz end0
mov rax, 1
mov [x], rax
jmp loop0
end0: nop
=======

mov rax, [x] 
push rax
mov rax, 20
mov rbx, rax
pop rax
add rax, rbx
mov [x], rax
>>>>>>> origin/typage

mov rax, [x]
mov rdi, fmt_int
mov rsi, rax
xor rax, rax
call printf

pop rbp
ret

<<<<<<< HEAD

=======
>>>>>>> origin/typage
