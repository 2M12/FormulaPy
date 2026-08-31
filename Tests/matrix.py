import time

def matrix_operations(n):
    total = 0
    for i in range(n):
        for j in range(100):
            val = (i * j + i + j) % 1000
            if val > 500:
                total += val
            else:
                total -= val
    return abs(total) % 1000000007

def image_filter_simulation(n):
    result = 0
    for i in range(n):
        pixel = (i * 13) % 256
        result = (result + pixel * pixel) % 1000000007
    return result

if __name__ == "__main__":
    tests = [
        ("Matrix operations (200K)", matrix_operations, 200_000),
        ("Image filter (20M)", image_filter_simulation, 20_000_000),
    ]

    total_time = 0
    for name, func, arg in tests:
        start = time.time()
        result = func(arg)
        elapsed = time.time() - start
        total_time += elapsed
        print(f"[{name}] Result: {result}, Time: {elapsed:.4f} sec")

    print(f"\nTOTAL: {total_time:.4f} sec")