int sum_array(int[10] arr) {
    int s = 0;
    for (int i = 0; i < 10; i++) {
        s = s + arr[i];
    }
    return(s);
}

int main() {
    int[10] my_arr = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100};
    int total = sum_array(my_arr);
    
    if (total > 500) {
        printf(1);
    } else {
        printf(0);
    }
    for (int i = 0; i < 10; i++) {
        printf(my_arr[i]);
    }
    
    printf(total);
    return(0);
}