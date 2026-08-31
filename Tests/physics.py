import time

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

if __name__ == "__main__":
    tests = [
        ("Particle simulation (10M)", simulate_particles, 10_000_000),
        ("Collision check (500K)", collision_check, 500_000),
    ]

    total_time = 0
    for name, func, arg in tests:
        start = time.time()
        result = func(arg)
        elapsed = time.time() - start
        total_time += elapsed
        print(f"[{name}] Result: {result}, Time: {elapsed:.4f} sec")

    print(f"\nTOTAL: {total_time:.4f} sec")