# Compression Methods Reference Guide

---

## Introduction

Compression reduces the size of data for storage or transmission.
Different methods optimize for speed, compression ratio, or resource usage.

---

# Common Compression Methods

## 1. **Zstandard (zstd)**
- **Strengths:** Extremely fast compression and decompression.
- **Compression Ratio:** Moderate to High.
- **Use Cases:** Realtime systems, backups, data streaming.
- **Special:** Tunable levels for ultra-fast or ultra-high compression.

## 2. **LZ4**
- **Strengths:** Very fast, extremely low CPU usage.
- **Compression Ratio:** Low to Moderate.
- **Use Cases:** Embedded systems, databases, filesystems.
- **Special:** Prioritizes speed over ratio.

## 3. **Bzip2**
- **Strengths:** High compression ratio.
- **Compression Ratio:** High.
- **Use Cases:** Long-term archival, old backups.
- **Special:** Slower than modern methods, heavy CPU usage.

## 4. **Gzip**
- **Strengths:** Universal support.
- **Compression Ratio:** Moderate.
- **Use Cases:** Web servers, file archives.
- **Special:** Very stable but older.

## 5. **LZMA / xz**
- **Strengths:** Extremely high compression.
- **Compression Ratio:** Very High.
- **Use Cases:** Software distribution, large backups.
- **Special:** Very slow to compress, faster to decompress.

---

# Choosing a Method

| Goal | Recommended Method |
|:---|:---|
| Maximum Speed | LZ4 |
| Balance of Speed and Ratio | Zstandard (zstd) |
| Maximum Compression | LZMA (xz) |
| Universal Compatibility | Gzip |
| High Ratio Older Systems | Bzip2 |

---

# Notes

- Always test compression/decompression speed for your specific workload.
- Balance storage savings against CPU time.
- Newer methods like Zstandard outperform legacy options in most cases.

---

(End of Compression Reference)

---

*Compiled for systems optimization studies.*
