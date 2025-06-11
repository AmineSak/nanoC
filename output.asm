; --- moule.asm ---
extern printf, atoi, malloc

section .data
    fmt_int:  db "%ld", 10, 0   ; Use %ld for 64-bit integers
    argv_ptr: dq 0

    t1: dq 0
t2: dq 0
s: dq 0
i: dq 0
                   ; Placeholder for global variables

section .text
global main

                       ; Placeholder for all user-defined functions

; --- Main function entry point ---
main:
    push rbp
    mov rbp, rsp
    sub rsp, 256                ; Reserve stack space for main's local variables
    
    ; Save command line arguments pointer
    mov [argv_ptr], rsi

                       ; Placeholder for initializing main's parameters from argv
    
    
    ; Allocate memory for array 't1'
    mov rax, 5
    mov rdi, rax
    mov rax, 8
    imul rdi, rax
    call malloc
    mov [t1], rax

    ; Initialize t1[0]
    mov rax, 10
    mov rbx, [t1]
    mov [rbx + 0], rax

    ; Initialize t1[1]
    mov rax, 20
    mov rbx, [t1]
    mov [rbx + 8], rax

    ; Initialize t1[2]
    mov rax, 30
    mov rbx, [t1]
    mov [rbx + 16], rax

    ; Initialize t1[3]
    mov rax, 40
    mov rbx, [t1]
    mov [rbx + 24], rax

    ; Initialize t1[4]
    mov rax, 50
    mov rbx, [t1]
    mov [rbx + 32], rax

    ; Allocate memory for array 't2'
    mov rax, 5
    mov rdi, rax             ; Number of elements
    mov rax, 8          ; Size of each element (int or pointer)
    imul rdi, rax            ; Total bytes
    call malloc
    mov [t2], rax    ; Store pointer in local variable 't2'

    mov rax, 0
    mov [s], rax  ; local var s

    ; For loop init
    mov rax, 0
    mov [rbp-32], rax
for_loop_0:
    ; For loop condition
    
    mov rax, 5
    push rax
    mov rax, [rbp-32]
    pop rbx
    cmp rax, rbx
setl al
movzx rax, al

    cmp rax, 0
    jz for_end_0
    ; For loop body
    
    
    mov rax, [rbp-32]
    mov rbx, rax                     ; rbx holds the index
    mov rax, [t1]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    push rax
    mov rax, [rbp-32]
    mov rbx, rax
    pop rax
    mov rcx, [t2]
    mov [rcx + rbx * 8], rax

    
    mov rax, [rbp-32]
    mov rbx, rax                     ; rbx holds the index
    mov rax, [t2]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    push rax
    mov rax, [s]
    pop rbx
    add rax, rbx

mov [s], rax
    ; For loop increment
    inc qword [rbp-32]
    jmp for_loop_0
for_end_0:
    nop

    mov rax, [s]
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    mov rax, [s]
    jmp main_epilogue
                    ; Placeholder for main's body
    
    ; Main function epilogue (return value in rax is the exit code)
main_epilogue:
    mov rsp, rbp
    pop rbp
    ret
