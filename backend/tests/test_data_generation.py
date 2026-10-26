"""Synthetic demonstrations must match their advertised assumptions."""

import numpy as np
import pandas as pd

from app.core.data_generation import generate_standard_events, get_sample_dataframe


def test_standard_sample_has_uncensored_positive_sales_and_broad_price_support():
    frame = generate_standard_events()
    assert len(frame) == 80
    assert frame.ticket_price.between(50, 170).all()
    assert frame.ticket_price.nunique() >= 10
    assert (frame.tickets_sold > 0).all()
    assert (frame.tickets_sold < frame.venue_capacity).all()
    assert (frame.venue_capacity >= 800).all()
    assert frame._synthetic.all()


def test_standard_generation_is_reproducible_and_keeps_quadratic_signal():
    first = generate_standard_events()
    pd.testing.assert_frame_equal(first, generate_standard_events())
    p = first.ticket_price.to_numpy(dtype=float)
    y = first.tickets_sold.to_numpy(dtype=float)
    # The mean observed noise should remain small relative to the demand scale.
    latent = 800 - 3.5 * p - .005 * p**2
    assert abs(float(np.mean(y - latent))) < 10
    assert float(np.std(y - latent)) < 25


def test_sellout_sample_preserves_intentional_censoring():
    frame = get_sample_dataframe("sellout")
    assert len(frame) == 40
    assert (frame.tickets_sold == frame.venue_capacity).any()
    assert (frame.tickets_sold <= frame.venue_capacity).all()
