"""R's default random numbers (Mersenne-Twister, set.seed, sample with "Rejection"), so a refit in
Python draws the same out-of-fold folds as refit_models.R and the two give identical models.
Checked against R in tests/test_rrng.py.
"""
from __future__ import annotations

import math

N, M = 624, 397
MATRIX_A, UPPER, LOWER = 0x9908B0DF, 0x80000000, 0x7FFFFFFF
I2_32M1 = 2.328306437080797e-10  # 1 / (2^32 - 1)


class RRandom:
    def __init__(self, seed: int):
        """set.seed(seed): R's RNG_Init for Mersenne-Twister."""
        s = seed & 0xFFFFFFFF
        for _ in range(50):
            s = (69069 * s + 1) & 0xFFFFFFFF
        table = []
        for _ in range(N + 1):
            s = (69069 * s + 1) & 0xFFFFFFFF
            table.append(s)
        self.mti = N            # FixupSeeds: dummy[0] = 624, so the first draw regenerates
        self.mt = table[1:]

    def _genrand(self) -> float:
        mt = self.mt
        if self.mti >= N:
            for kk in range(N - M):
                y = (mt[kk] & UPPER) | (mt[kk + 1] & LOWER)
                mt[kk] = mt[kk + M] ^ (y >> 1) ^ (MATRIX_A if y & 1 else 0)
            for kk in range(N - M, N - 1):
                y = (mt[kk] & UPPER) | (mt[kk + 1] & LOWER)
                mt[kk] = mt[kk + (M - N)] ^ (y >> 1) ^ (MATRIX_A if y & 1 else 0)
            y = (mt[N - 1] & UPPER) | (mt[0] & LOWER)
            mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ (MATRIX_A if y & 1 else 0)
            self.mti = 0
        y = mt[self.mti]
        self.mti += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        return y * 2.3283064365386963e-10

    def unif_rand(self) -> float:
        x = self._genrand()
        if x <= 0.0:
            return 0.5 * I2_32M1
        if 1.0 - x <= 0.0:
            return 1.0 - 0.5 * I2_32M1
        return x

    def _rbits(self, bits: int) -> int:
        v = 0
        for _ in range(0, bits + 1, 16):
            v = 65536 * v + int(math.floor(self.unif_rand() * 65536))
        return v & ((1 << bits) - 1)

    def unif_index(self, dn: int) -> int:
        """R_unif_index under sample.kind = "Rejection" (R >= 3.6)."""
        if dn <= 0:
            return 0
        bits = math.ceil(math.log2(dn))
        while True:
            dv = self._rbits(bits)
            if dn > dv:
                return dv

    def sample(self, x: list) -> list:
        """sample(x): a random permutation of x."""
        n = len(x)
        idx = list(range(n))
        out = []
        for _ in range(len(x)):
            j = self.unif_index(n)
            out.append(x[idx[j]])
            n -= 1
            idx[j] = idx[n]
        return out
