int main(int x)
{
    int[5] t1 = {10, 20, 30, 40, 50};
    int[5] t2;

    int s = 0;

    for (int i = 0; i < 5; i++)
    {
        t2[i] = t1[i];
        s = s + t2[i];
    }

    printf(s);
    return (s);
}