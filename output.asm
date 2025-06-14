; --- moule.asm ---
extern printf, atoi, malloc

section .data
    fmt_int:  db "%ld", 10, 0   ; Use %ld for 64-bit integers
    argv_ptr: dq 0

    my_arr: dq 0
total: dq 0
                   ; Placeholder for global variables

section .text
global main


; --- Function: sum_array ---
sum_array:
    push rbp
    mov rbp, rsp
    sub rsp, 256
    mov [rbp-8], rdi ; Save param 'arr'

    mov rax, 0
    mov [rbp-16], rax  ; local var s


    ; Allocate memory for array 't'
    mov rax, 2
    mov rdi, rax
    mov rax, 8
    imul rdi, rax
    call malloc
    mov [rbp-24], rax

    ; Initialize t[0]
    mov rax, 1
    mov rbx, [rbp-24]
    mov [rbx + 0], rax

    ; Initialize t[1]
    mov rax, 2
    mov rbx, [rbp-24]
    mov [rbx + 8], rax


    ; For loop init
    mov rax, 0
    mov [rbp-32], rax
for_loop_0:
    ; For loop condition
    
    mov rax, 10
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
    mov rax, [rbp-8]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    push rax
    mov rax, [rbp-16]
    pop rbx
    add rax, rbx

mov [rbp-16], rax
    
    mov rax, [rbp-32]
    mov rbx, rax                     ; rbx holds the index
    mov rax, [rbp-8]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    mov rax, [rbp-16]
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    ; For loop increment
    inc qword [rbp-32]
    jmp for_loop_0
for_end_0:
    nop


    mov rax, [rbp-16]
    jmp sum_array_epilogue


sum_array_epilogue:
    mov rsp, rbp
    pop rbp
    ret

; --- Function: fib ---
fib:
    push rbp
    mov rbp, rsp
    sub rsp, 256
    mov [rbp-8], rdi ; Save param 'n'
    mov [rbp-16], rsi ; Save param 'memo'

    
    mov rax, 2
    mov rbx, rax                     ; rbx holds the index
    mov rax, [rbp-16]    ; rax holds the base pointer
    mov rax, [rax + rbx * 8]         ; Access the element (8 bytes for int/pointer)

    mov [rbp-24], rax  ; local var i


    
    mov rax, 1
    push rax
    mov rax, [rbp-8]
    pop rbx
    cmp rax, rbx
setle al
movzx rax, al

    cmp rax, 0
    jz endif1

    mov rax, [rbp-8]
    jmp fib_epilogue

endif1: nop


    
    
    mov rax, 2
    push rax
    mov rax, [rbp-8]
    pop rbx
    sub rax, rbx

push rax
mov rax, [rbp-16]
push rax
pop rsi
pop rdi
call fib

    push rax
    
    mov rax, 1
    push rax
    mov rax, [rbp-8]
    pop rbx
    sub rax, rbx

push rax
mov rax, [rbp-16]
push rax
pop rsi
pop rdi
call fib

    pop rbx
    add rax, rbx

    jmp fib_epilogue


fib_epilogue:
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
    
    
    ; Allocate memory for array 'my_arr'
    mov rax, 10
    mov rdi, rax
    mov rax, 8
    imul rdi, rax
    call malloc
    mov [my_arr], rax

    ; Initialize my_arr[0]
    mov rax, 10
    mov rbx, [my_arr]
    mov [rbx + 0], rax

    ; Initialize my_arr[1]
    mov rax, 20
    mov rbx, [my_arr]
    mov [rbx + 8], rax

    ; Initialize my_arr[2]
    mov rax, 30
    mov rbx, [my_arr]
    mov [rbx + 16], rax

    ; Initialize my_arr[3]
    mov rax, 40
    mov rbx, [my_arr]
    mov [rbx + 24], rax

    ; Initialize my_arr[4]
    mov rax, 50
    mov rbx, [my_arr]
    mov [rbx + 32], rax

    ; Initialize my_arr[5]
    mov rax, 60
    mov rbx, [my_arr]
    mov [rbx + 40], rax

    ; Initialize my_arr[6]
    mov rax, 70
    mov rbx, [my_arr]
    mov [rbx + 48], rax

    ; Initialize my_arr[7]
    mov rax, 80
    mov rbx, [my_arr]
    mov [rbx + 56], rax

    ; Initialize my_arr[8]
    mov rax, 90
    mov rbx, [my_arr]
    mov [rbx + 64], rax

    ; Initialize my_arr[9]
    mov rax, 100
    mov rbx, [my_arr]
    mov [rbx + 72], rax

    mov rax, [my_arr]
push rax
pop rdi
call sum_array

    mov [total], rax  ; local var total

    
    mov rax, 500
    push rax
    mov rax, [total]
    pop rbx
    cmp rax, rbx
setg al
movzx rax, al

    cmp rax, 0
    jz else2

    mov rax, 1
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    jmp endif2
else2:

    mov rax, 0
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

endif2: nop

    mov rax, [total]
    mov rsi, rax
    mov rdi, fmt_int
    xor rax, rax
    call printf

    mov rax, 7
push rax
mov rax, [my_arr]
push rax
pop rsi
pop rdi
call fib

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
