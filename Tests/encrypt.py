import time

def encryption_simulation(n):
    encrypted = 0
    for i in range(n):
        key = (i * 7919) % 1000000007
        encrypted = (encrypted ^ key) % 1000000007
    return encrypted

def checksum_calculation(n):
    checksum = 0
    for i in range(n):
        checksum = (checksum + (i * 31) % 9973) % 1000000007
    return checksum

if __name__ == "__main__":
    tests = [
        ("Encryption (15M)", encryption_simulation, 15_000_000),
        ("Checksum (25M)", checksum_calculation, 25_000_000),
    ]

    total_time = 0
    for name, func, arg in tests:
        start = time.time()
        result = func(arg)
        elapsed = time.time() - start
        total_time += elapsed
        print(f"[{name}] Result: {result}, Time: {elapsed:.4f} sec")

    print(f"\nTOTAL: {total_time:.4f} sec")