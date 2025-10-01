import colorsys
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from osrs_recolor_gui import (
    apply_brightness_exponent,
    extract_ints_from_bracket_block,
    find_array_after,
    find_id,
    find_name,
    hsl_bits_to_floats_osrs_offsets,
    hsl_bits_to_rgb01_rebecca,
    pack_hsl,
    rgb01_to_rgb8,
    rgb01_to_rgb8_round,
    rgb_to_argb_int,
    shade_lightness_on_index,
    split_curly_blocks,
    unpack_hsl,
)


def test_pack_unpack_roundtrip():
    for h in (0, 31, 63):
        for s in (0, 3, 7):
            for l in (0, 64, 127):
                packed = pack_hsl(h, s, l)
                assert unpack_hsl(packed) == (h, s, l)


def test_osrs_offset_conversion():
    h, s, l = hsl_bits_to_floats_osrs_offsets(0, 0, 0)
    assert math.isclose(h, 1.0 / 128.0)
    assert math.isclose(s, 1.0 / 16.0)
    assert math.isclose(l, 0.0)

    h2, s2, l2 = hsl_bits_to_floats_osrs_offsets(63, 7, 127)
    assert math.isclose(h2, 63 / 64.0 + 1.0 / 128.0)
    assert math.isclose(s2, 7 / 8.0 + 1.0 / 16.0)
    assert math.isclose(l2, 127 / 128.0)

def test_apply_brightness_exponent_identity():
    rgb = (0.25, 0.5, 0.75)
    assert apply_brightness_exponent(rgb, None) == rgb
    assert apply_brightness_exponent(rgb, 1.0) == rgb


def test_apply_brightness_exponent_changes_values():
    rgb = (0.25, 0.5, 0.75)
    darker = apply_brightness_exponent(rgb, 2.0)
    assert darker[0] < rgb[0]
    assert darker[1] < rgb[1]
    assert darker[2] < rgb[2]


def test_rgb01_to_rgb8_and_argb_sign():
    rgb = rgb01_to_rgb8((1.0, 1.0, 1.0))
    assert rgb == (255, 255, 255)
    assert rgb_to_argb_int(*rgb) == -1


def test_rebecca_conversion_matches_colorsys():
    samples = [
        (0, 0, 0),
        (10, 2, 32),
        (31, 5, 90),
        (63, 7, 127),
    ]
    for h, s, l in samples:
        rgb = hsl_bits_to_rgb01_rebecca(h, s, l)
        expected = colorsys.hls_to_rgb(((h / 63.0) if h else 0.0) % 1.0, l / 127.0, s / 7.0)
        assert math.isclose(rgb[0], expected[0], rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(rgb[1], expected[1], rel_tol=1e-9, abs_tol=1e-9)
        assert math.isclose(rgb[2], expected[2], rel_tol=1e-9, abs_tol=1e-9)


def test_rgb01_to_rgb8_round_rounds_nearest():
    rgb = rgb01_to_rgb8_round((0.5, 0.5, 0.5))
    assert rgb == (128, 128, 128)


def test_shade_lightness_on_index_clamps():
    idx = pack_hsl(10, 2, 50)
    shaded = shade_lightness_on_index(idx, scale=0.5, lmin=40, lmax=60)
    h, s, l = unpack_hsl(shaded)
    assert (h, s) == (10, 2)
    assert l == 40  # clamped to minimum after scaling


def test_split_curly_blocks_handles_nested():
    text = "before {outer {inner} still outer} after {two}"
    blocks = split_curly_blocks(text)
    assert blocks == ["{outer {inner} still outer}", "{two}"]


def test_extract_ints_from_block_filters_range():
    block = "[\n 1\n -2\n 70000\n 42\n]"
    assert extract_ints_from_bracket_block(block) == [1, 42]


def test_find_array_after_matches_case_insensitive():
    text = "recolorTo: (3)[\n 100\n 200\n 300\n ]"
    assert find_array_after("recolorTo", text) == [100, 200, 300]


def test_find_id_and_name():
    text = 'id: 1234\nname: "Tester"\n'
    assert find_id(text) == 1234
    assert find_name(text) == "Tester"
