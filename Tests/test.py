import time

def heavy_calc(n):
    total = 0
    for i in range(n):
        total = (total + i * 3) % 1000000007
    return total

def sum_loop(n):
    total = 0
    for i in range(n):
        total += i % 1000
    return total

def multiply_loop(n):
    result = 1
    for i in range(1, n):
        result = (result * 2) % 1000000007
    return result

if __name__ == "__main__":
    tests = [
        ("Heavy calc (10M)", heavy_calc, 10_000_000),
        ("Sum loop (20M)", sum_loop, 20_000_000),
        ("Multiply loop (5M)", multiply_loop, 5_000_000),
    ]

    total_time = 0
    for name, func, arg in tests:
        start = time.time()
        result = func(arg)
        elapsed = time.time() - start
        total_time += elapsed
        print(f"[{name}] Result: {result}, Time: {elapsed:.4f} sec")

    print(f"\nTOTAL: {total_time:.4f} sec")