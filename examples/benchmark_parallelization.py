"""
Benchmark demonstrating the performance benefits of parallelization.

This script compares sequential vs parallel I/O operations to show
the real-world speedup from using asyncio.gather.
"""

import asyncio
import time
from pathlib import Path

from PIL import Image

from gemini_imagen.s3_utils import save_image


async def simulate_slow_network_save(image: Image.Image, path: str, delay: float = 0.5):
    """Simulate a slow network save (e.g., to S3) with artificial delay."""
    # Add delay to simulate network latency
    await asyncio.sleep(delay)
    # Actually save the image
    location, s3_uri, http_url = await save_image(image, path)
    return location, s3_uri, http_url


async def benchmark_sequential(images: list[Image.Image], output_dir: Path, delay: float):
    """Save images sequentially (one at a time)."""
    print("\n🐌 Sequential Save (Old Method)")
    print("-" * 50)

    start_time = time.time()
    results = []

    for i, img in enumerate(images):
        output_path = output_dir / f"sequential_{i}.png"
        print(f"  Saving image {i + 1}/{len(images)}...", end=" ", flush=True)
        result = await simulate_slow_network_save(img, str(output_path), delay)
        results.append(result)
        print(f"✓ ({time.time() - start_time:.2f}s elapsed)")

    total_time = time.time() - start_time
    print(f"\n⏱️  Total time: {total_time:.2f} seconds")
    return results, total_time


async def benchmark_parallel(images: list[Image.Image], output_dir: Path, delay: float):
    """Save images in parallel using asyncio.gather."""
    print("\n⚡ Parallel Save (New Method with asyncio.gather)")
    print("-" * 50)

    start_time = time.time()

    # Prepare all save tasks
    save_tasks = [
        simulate_slow_network_save(img, str(output_dir / f"parallel_{i}.png"), delay)
        for i, img in enumerate(images)
    ]

    print(f"  Starting {len(images)} saves in parallel...", flush=True)

    # Execute all saves in parallel
    results = await asyncio.gather(*save_tasks)

    total_time = time.time() - start_time
    print(f"  ✓ All {len(images)} images saved!")
    print(f"\n⏱️  Total time: {total_time:.2f} seconds")
    return results, total_time


async def main():
    """Run the benchmark comparison."""
    print("\n" + "=" * 70)
    print("  PARALLELIZATION PERFORMANCE BENCHMARK")
    print("=" * 70)

    # Configuration
    num_images = 5
    network_delay = 0.5  # Simulate 500ms network latency per save
    output_dir = Path("benchmark_output")
    output_dir.mkdir(exist_ok=True)

    print("\nConfiguration:")
    print(f"  • Number of images: {num_images}")
    print(f"  • Simulated network delay per save: {network_delay}s")
    print(f"  • Output directory: {output_dir}")

    # Create sample images
    print(f"\nCreating {num_images} sample images...")
    images = [
        Image.new("RGB", (100, 100), color=f"#{i * 50:02x}{i * 30:02x}{i * 20:02x}")
        for i in range(num_images)
    ]
    print(f"  ✓ Created {len(images)} images")

    # Run sequential benchmark
    _seq_results, seq_time = await benchmark_sequential(images, output_dir, network_delay)

    # Run parallel benchmark
    _par_results, par_time = await benchmark_parallel(images, output_dir, network_delay)

    # Calculate and display results
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)

    speedup = seq_time / par_time if par_time > 0 else 0
    time_saved = seq_time - par_time

    print(f"\nSequential: {seq_time:.2f}s")
    print(f"Parallel:   {par_time:.2f}s")
    print(f"\n🚀 Speedup:     {speedup:.2f}x faster")
    print(f"⏰ Time saved:  {time_saved:.2f}s ({time_saved / seq_time * 100:.1f}% reduction)")

    # Theoretical vs actual
    theoretical_time = network_delay  # Should take about 1 network delay in parallel
    efficiency = (theoretical_time / par_time) * 100 if par_time > 0 else 0

    print(f"\n📊 Efficiency: {efficiency:.1f}% (actual vs theoretical parallel time)")
    print(f"   Theoretical minimum: {theoretical_time:.2f}s")
    print(f"   Actual parallel:     {par_time:.2f}s")

    # Scaling analysis
    print("\n📈 Scaling Analysis:")
    print(f"   As you add more images, parallel stays ~{network_delay:.1f}s")
    print(f"   Sequential grows linearly: N x {network_delay:.1f}s")
    print("\n   Examples:")
    for n in [1, 2, 3, 5, 10, 20]:
        seq_est = n * network_delay
        par_est = network_delay  # Stays constant
        speedup_est = seq_est / par_est
        print(
            f"   • {n:2d} images: {seq_est:5.1f}s -> {par_est:4.1f}s  ({speedup_est:4.1f}x speedup)"
        )

    # Cleanup
    print("\n🧹 Cleaning up benchmark files...")
    for file in output_dir.glob("*.png"):
        file.unlink()
    output_dir.rmdir()
    print("   ✓ Cleanup complete")

    print("\n" + "=" * 70)
    print("Benchmark complete! The parallel approach is significantly faster.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
