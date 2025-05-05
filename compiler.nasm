extern printf

section .data
    x: dq 0
    y: dq 0
    ; ...
    ; ...
    ; toutes les variables

global main 
section .text
main:
push rbp
mov rbx,[rsi+8] ; get the first arg of main
mov rdi, rbx
call atoi
mov [x], rax

xor rax,rax
mov rdi, hello
mov rsi, 12
mov rsi,[x]
call printf
pop rbp
ret
    push rbp
    
    ; code ....

    pop rbp 
    ret
