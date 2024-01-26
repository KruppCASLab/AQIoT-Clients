#include <cstdio>

#include "pico/stdlib.h"

[[noreturn]] int main()
{
    stdio_init_all();
    while (true) {
        printf("Hello AQIoT!\n");
        sleep_ms(1000);
    }
}
