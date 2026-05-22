from datetime import date
import pytest
from services.muhurat import (
    compute_muhurat, compute_muhurat_by_id, _vedic_weekday,
)

# Varanasi
LAT, LON, TZ = 25.3176, 82.9739, "Asia/Kolkata"


def test_vedic_weekday():
    # 2026-05-19 is a Tuesday → Vedic = 2
    assert _vedic_weekday(date(2026, 5, 19)) == 2
    # 2026-05-17 is Sunday → Vedic = 0
    assert _vedic_weekday(date(2026, 5, 17)) == 0


def test_bundle_has_all_windows():
    b = compute_muhurat(date(2026, 5, 19), LAT, LON, TZ)
    assert len(b.auspicious) == 5
    assert len(b.inauspicious) >= 4  # 3 kaals + 1-2 dur muhurats
    ids = {w.id for w in b.auspicious}
    assert ids == {"brahma", "abhijit", "vijay", "godhuli", "amrit"}


def test_abhijit_centered_on_noon():
    b = compute_muhurat(date(2026, 5, 19), LAT, LON, TZ)
    abhijit = next(w for w in b.auspicious if w.id == "abhijit")
    # Width should be ~48 minutes
    width_min = (abhijit.end - abhijit.start).total_seconds() / 60
    assert 40 <= width_min <= 56


def test_rahu_kaal_position_tuesday():
    # Tuesday → Rahu Kaal is 7th of 8 parts (late afternoon)
    b = compute_muhurat(date(2026, 5, 19), LAT, LON, TZ)
    rahu = next(w for w in b.inauspicious if w.id == "rahu")
    # Should land in afternoon
    assert 14 <= rahu.start.hour <= 16


def test_lookup_by_id():
    w = compute_muhurat_by_id("abhijit", date(2026, 5, 19), LAT, LON, TZ)
    assert w is not None
    assert w.name == "Abhijit Muhurat"

    missing = compute_muhurat_by_id("nonexistent", date(2026, 5, 19), LAT, LON, TZ)
    assert missing is None