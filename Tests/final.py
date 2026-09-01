import time

def for_loop_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total % 1000000007

def while_loop_count(n):
    count = 0
    i = 0
    while i < n:
        count += i
        i += 1
    return count % 1000000007

def nested_for(n):
    total = 0
    for i in range(n):
        for j in range(50):
            total += (i * j) % 1000
    return total % 1000000007

def hash_simulation(n):
    h = 0
    for i in range(n):
        h = (h * 31 + i * 7) % 1000000007
    return h

def encryption_rounds(n):
    data = 12345
    for i in range(n):
        data = (data * 1103515245 + 12345) % 2147483648
    return data

def checksum(n):
    total = 0
    for i in range(n):
        total = (total + (i * 2654435761) % 4294967296) % 1000000007
    return total

def simulate_particles(n):
    position = 0
    velocity = 1
    total_distance = 0
    for i in range(n):
        position += velocity
        velocity += 1
        if velocity > 100:
            velocity = 1
        total_distance += abs(position)
    return total_distance % 1000000007

def collision_check(n):
    collisions = 0
    for i in range(n):
        for j in range(100):
            if (i * j) % 97 == 0:
                collisions += 1
    return collisions % 1000000007

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
        ("For loop sum (50M)", for_loop_sum, 50_000_000),
        ("While loop (30M)", while_loop_count, 30_000_000),
        ("Nested for (500K)", nested_for, 500_000),
        ("Hash simulation (50M)", hash_simulation, 50_000_000),
        ("Encryption (30M)", encryption_rounds, 30_000_000),
        ("Checksum (40M)", checksum, 40_000_000),
        ("Particle simulation (10M)", simulate_particles, 10_000_000),
        ("Collision check (500K)", collision_check, 500_000),
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