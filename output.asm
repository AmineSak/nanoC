; --- moule.asm ---
extern printf, atoi, malloc

section .data
    fmt_int:  db "%ld", 10, 0   ; Use %ld for 64-bit integers
    argv_ptr: dq 0

                       ; Placeholder for global variables

section .text
global main


; --- Function: recurs ---
recurs:
    push rbp
    mov rbp, rsp
    sub rsp, 256
    mov [rbp-16], rdi ; Save param 'n'

    
    mov rax, 10
    push rax
    mov rax, [rbp-16]
    pop rbx
    cmp rax, rbx
setle al
movzx rax, al

    cmp rax, 0
    jz endif0

    mov rax, [rbp-16]
    jmp recurs_epilogue

endif0: nop


    
    
    mov rax, 1
    push rax
    mov rax, [rbp-16]
    pop rbx
    sub rax, rbx

push rax
pop rdi
call recurs

    push rax
    mov rax, [rbp-16]
    pop rbx
    add rax, rbx

    jmp recurs_epilogue


recurs_epilogue:
    mov rsp, rbp
    pop rbp
    ret
                       ; Placeholder for all user-defined functions

; --- Main function entry point ---
main:
    push rbp
    mov rbp, rsp
    sub rsp, 256                ; Reserve stack space for main's local variables
    
    ; Save command line arguments pointer
    mov [argv_ptr], rsi

                       ; Placeholder for initializing main's parameters from argv
    
    
    ; Allocate memory for array 'tab'
    mov rax, 6
    mov rdi, rax
    mov rax, 8
    imul rdi, rax
    call malloc
    mov [rbp-8], rax

    ; Initialize tab[0]
    mov rax, 1
    mov rbx, [rbp-8]
    mov [rbx + 0], rax

    ; Initialize tab[1]
    mov rax, 2
    mov rbx, [rbp-8]
    mov [rbx + 8], rax

    ; Initialize tab[2]
    mov rax, 4
    mov rbx, [rbp-8]
    mov [rbx + 16], rax

    ; Initialize tab[3]
    mov rax, 5
    mov rbx, [rbp-8]
    mov [rbx + 24], rax

    ; Initialize tab[4]
    mov rax, 6
    mov rbx, [rbp-8]
    mov [rbx + 32], rax

    ; Initialize tab[5]
    mov rax, 8
    mov rbx, [rbp-8]
    mov [rbx + 40], rax

    ; For loop init
    mov rax, 0
    mov [rbp-16], rax
for_loop_1:
    ; For loop condition
    
    mov rax, 5
    push rax
    mov rax, [rbp-16]
    pop rbx
    cmp rax, rbx
setl al
movzx rax, al

    cmp rax, 0
    jz for_end_1
    ; For loop body
    
    
    mov rax, [rbp-16]
    mov rbx, rax                     ; rbx holds the index
    mov rax, [rbp-8]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    mov [rbp-24], rax  ; local var val

    mov rax, [rbp-24]
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    ; For loop increment
    inc qword [rbp-16]
    jmp for_loop_1
for_end_1:
    nop

    mov rax, 0
    jmp main_epilogue
                    ; Placeholder for main's body
    
    ; Main function epilogue (return value in rax is the exit code)
main_epilogue:
    mov rsp, rbp
    pop rbp
    ret
