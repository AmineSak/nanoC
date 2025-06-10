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
    
    
    mov rax, 12
    mov [rbp-8], rax  ; local var a

    mov rax, [rbp-8]
push rax
pop rdi
call recurs

    mov [rbp-16], rax  ; local var result

    mov rax, [rbp-16]
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    mov rax, 0
    jmp main_epilogue
                    ; Placeholder for main's body
    
    ; Main function epilogue (return value in rax is the exit code)
main_epilogue:
    mov rsp, rbp
    pop rbp
    ret
