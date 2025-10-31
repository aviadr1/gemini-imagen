# Parallelization Performance Demonstration

This document demonstrates how `asyncio.gather` accelerates image downloads and uploads in the gemini-imagen library.

## Overview

The library now uses **parallel I/O operations** for loading multiple input images and saving multiple output images, resulting in significant performance improvements.

---

## 1. Loading Input Images (Downloads)

### Before: Sequential Loading ❌

```python
# OLD CODE (Sequential - SLOW)
async def _build_content_with_labels(self, input_images):
    for img_source in input_images:
        loaded_img, info = await self._load_single_image(img_source, label)
        # ⏳ Wait for each image to download completely before starting the next
        content.append(loaded_img)
```

**Timeline for 3 images (each takes 2 seconds to download):**
```
Image 1: [████████████████] 2s
Image 2:                  [████████████████] 2s
Image 3:                                   [████████████████] 2s

Total Time: 6 seconds ⏱️
```

### After: Parallel Loading ✅

```python
# NEW CODE (Parallel - FAST)
async def _build_content_with_labels(self, input_images):
    # Prepare all loading tasks
    load_tasks = [(label, img) for label, img in input_images]

    # Load ALL images in parallel using asyncio.gather
    loaded_results = await asyncio.gather(
        *[self._load_single_image(img, label) for label, img in load_tasks]
    )
    # ⚡ All images download simultaneously!
```

**Timeline for 3 images (all download at the same time):**
```
Image 1: [████████████████] 2s
Image 2: [████████████████] 2s
Image 3: [████████████████] 2s

Total Time: ~2 seconds ⏱️
```

**Performance Gain: 3x faster** 🚀

---

## 2. Saving Output Images (Uploads)

### Before: Sequential Saving ❌

```python
# OLD CODE (Sequential - SLOW)
async def _save_and_log_images(self, result, output_specs):
    for idx, (img, (label, location)) in enumerate(zip(result.images, output_specs)):
        location_str, s3_uri, http_url = await save_image(img, location, ...)
        # ⏳ Wait for each upload to S3 to complete before starting the next
        result.image_locations.append(location_str)
```

**Timeline for 3 images (each takes 1.5 seconds to upload):**
```
Upload 1: [████████████] 1.5s
Upload 2:              [████████████] 1.5s
Upload 3:                           [████████████] 1.5s

Total Time: 4.5 seconds ⏱️
```

### After: Parallel Saving ✅

```python
# NEW CODE (Parallel - FAST)
async def _save_and_log_images(self, result, output_specs):
    # Prepare all save tasks
    save_tasks = [
        save_image(img, location, ...)
        for img, (label, location) in zip(result.images, output_specs)
    ]

    # Save ALL images in parallel using asyncio.gather
    save_results = await asyncio.gather(*save_tasks)
    # ⚡ All images upload simultaneously!
```

**Timeline for 3 images (all upload at the same time):**
```
Upload 1: [████████████] 1.5s
Upload 2: [████████████] 1.5s
Upload 3: [████████████] 1.5s

Total Time: ~1.5 seconds ⏱️
```

**Performance Gain: 3x faster** 🚀

---

## 3. Real-World Example

### Scenario: Processing a batch of images with HTTP inputs and S3 outputs

```python
import asyncio
from gemini_imagen import GeminiImageGenerator

async def process_batch():
    generator = GeminiImageGenerator()

    # Input: 5 images from HTTP URLs (each takes ~1.5s to download)
    # Output: 3 generated images to S3 (each takes ~1s to upload)

    result = await generator.generate(
        prompt="Combine these architectural styles into a modern design",
        input_images=[
            "https://example.com/building1.jpg",  # 1.5s download
            "https://example.com/building2.jpg",  # 1.5s download
            "https://example.com/building3.jpg",  # 1.5s download
            "https://example.com/building4.jpg",  # 1.5s download
            "https://example.com/building5.jpg",  # 1.5s download
        ],
        output_images=[
            "s3://my-bucket/design1.png",  # 1s upload
            "s3://my-bucket/design2.png",  # 1s upload
            "s3://my-bucket/design3.png",  # 1s upload
        ]
    )
```

### Performance Comparison

#### Sequential (Old):
```
Downloads: 1.5s × 5 = 7.5s ⏳
Gemini API: 3s ⏳
Uploads: 1s × 3 = 3s ⏳
─────────────────────────
Total: 13.5 seconds
```

#### Parallel (New):
```
Downloads: max(1.5s × 5) = 1.5s ⚡ (all parallel)
Gemini API: 3s ⏳
Uploads: max(1s × 3) = 1s ⚡ (all parallel)
─────────────────────────
Total: 5.5 seconds
```

**Total Speedup: 2.45x faster overall** 🎯

---

## 4. How asyncio.gather Works

### Visualization

```python
# Sequential execution (one at a time)
result1 = await download_image_1()  # Wait...
result2 = await download_image_2()  # Wait...
result3 = await download_image_3()  # Wait...

# Parallel execution (all at once)
results = await asyncio.gather(
    download_image_1(),  # Start all three immediately
    download_image_2(),  # All running concurrently
    download_image_3(),  # Waiting happens in parallel
)
```

### Key Benefits:

1. **I/O-bound operations don't block each other**
   - While waiting for network I/O (HTTP download, S3 upload), other operations can proceed
   - CPU stays active managing multiple concurrent operations

2. **Network bandwidth is fully utilized**
   - Multiple connections open simultaneously
   - Takes advantage of modern network infrastructure

3. **Latency is hidden**
   - Network round-trip time for one image ≈ same as for multiple images
   - Only limited by bandwidth, not latency

---

## 5. Code Locations

### Input Image Loading (Parallel)
**File:** `src/gemini_imagen/gemini_image_wrapper.py`
**Lines:** 427-430

```python
# Load all images in parallel using asyncio.gather
loaded_results = await asyncio.gather(
    *[self._load_single_image(img, label) for label, img in load_tasks]
)
```

### Output Image Saving (Parallel)
**File:** `src/gemini_imagen/gemini_image_wrapper.py`
**Lines:** 627-640

```python
# Prepare save tasks for parallel execution
save_tasks = [
    save_image(img, location, region=..., ...)
    for img, (label, location) in zip(result.images, output_specs)
]

# Save all images in parallel using asyncio.gather
save_results = await asyncio.gather(*save_tasks)
```

---

## 6. Performance Scaling

The speedup scales linearly with the number of images:

| Number of Images | Sequential Time | Parallel Time | Speedup |
|------------------|-----------------|---------------|---------|
| 1 image          | 2s             | 2s            | 1x      |
| 2 images         | 4s             | 2s            | 2x      |
| 3 images         | 6s             | 2s            | 3x      |
| 5 images         | 10s            | 2s            | 5x      |
| 10 images        | 20s            | 2s            | 10x     |

*Assumes each image takes 2 seconds to download and network can handle concurrent connections.*

---

## 7. Technical Details

### Why This Works

1. **Async/Await Pattern:**
   - `await` doesn't block the thread, it yields control to the event loop
   - Event loop can start other operations while waiting for I/O

2. **asyncio.gather:**
   - Creates tasks for all coroutines immediately
   - Waits for ALL tasks to complete
   - Returns results in the same order as input

3. **Non-blocking I/O:**
   - `aiohttp` for HTTP downloads (async HTTP client)
   - `aioboto3` for S3 uploads (async AWS SDK)
   - `aiofiles` for local file operations (async file I/O)

### Order Preservation

Even though operations run in parallel, results are returned in the correct order:

```python
loaded_results = await asyncio.gather(
    load_image("image1.jpg"),  # May finish 2nd
    load_image("image2.jpg"),  # May finish 1st
    load_image("image3.jpg"),  # May finish 3rd
)
# Results are always: [image1, image2, image3]
# Order matches input order, not completion order
```

---

## Summary

✅ **Input images load in parallel** - All HTTP/S3 downloads happen simultaneously
✅ **Output images save in parallel** - All S3 uploads happen simultaneously
✅ **Order is preserved** - Results match input order
✅ **Significant speedup** - 3-10x faster for typical batch operations
✅ **No code changes needed** - Users automatically get the performance boost

The parallelization is completely transparent to users - the API remains the same, but operations are much faster!
