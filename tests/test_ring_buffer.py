import numpy as np

from voicekeyboard.stt import RingBuffer


def test_ring_buffer_append_and_concat():
    rb = RingBuffer(capacity=10)
    rb.append(np.array([1, 2, 3], dtype=np.float32))
    rb.append(np.array([4, 5], dtype=np.float32))
    out = rb.concat()
    assert out.tolist() == [1, 2, 3, 4, 5]


def test_ring_buffer_eviction():
    rb = RingBuffer(capacity=5)
    rb.append(np.array([1, 2, 3], dtype=np.float32))
    rb.append(np.array([4, 5, 6], dtype=np.float32))  # total 6, capacity 5 -> evict from left
    out = rb.concat()
    assert out.tolist() == [2, 3, 4, 5, 6]


def test_ring_buffer_clear():
    rb = RingBuffer(capacity=4)
    rb.append(np.array([1, 2, 3], dtype=np.float32))
    rb.clear()
    out = rb.concat()
    assert out.size == 0

