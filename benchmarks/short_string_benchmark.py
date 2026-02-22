"""Benchmark pySBD on short strings (2-3 sentences) across languages."""

import time

import pysbd

SAMPLES = {
    "en": "Dr. Smith went to Washington. He arrived on Jan. 5th at 3 P.M. and met with Sen. Jones.",
    "es": "El Dr. García fue a Madrid. Llegó el 5 de ene. a las 3 p.m.",
    "de": "Herr Dr. Müller ging nach Berlin. Er kam am 5. Jan. um 15 Uhr an.",
    "fr": "M. Dupont est allé à Paris. Il est arrivé le 5 janv. à 15 h.",
    "it": "Il dott. Rossi è andato a Roma. È arrivato il 5 gen. alle 15.",
    "ru": "Доктор Иванов поехал в Москву. Он прибыл 5 января в 15:00.",
    "zh": "史密斯博士去了华盛顿。他于1月5日下午3点到达。",
    "ja": "スミス博士はワシントンに行きました。彼は1月5日の午後3時に到着しました。",
    "pl": "Dr. Kowalski pojechał do Warszawy. Przyjechał 5 stycznia o godz. 15.",
    "ar": "ذهب الدكتور أحمد إلى القاهرة. وصل في الخامس من يناير.",
}

N_ITERATIONS = 5000


def benchmark_language(lang_code, text, n=N_ITERATIONS):
    seg = pysbd.Segmenter(language=lang_code, clean=False, char_span=False)
    # Warmup
    for _ in range(50):
        seg.segment(text)
    # Timed run
    start = time.perf_counter()
    for _ in range(n):
        seg.segment(text)
    elapsed = time.perf_counter() - start
    return elapsed


def main():
    print(f"pySBD short-string benchmark  ({N_ITERATIONS} iterations each)")
    print("=" * 62)
    total = 0.0
    for lang, text in SAMPLES.items():
        elapsed = benchmark_language(lang, text)
        us_per_call = elapsed / N_ITERATIONS * 1_000_000
        total += elapsed
        print(f"  {lang}:  {us_per_call:8.1f} µs/call   ({elapsed:.3f}s total)")
    total_us = total / (N_ITERATIONS * len(SAMPLES)) * 1_000_000
    print("-" * 62)
    print(f"  avg: {total_us:8.1f} µs/call")
    print(f"  total wall time: {total:.3f}s")


if __name__ == "__main__":
    main()
