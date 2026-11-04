"""백팩: 판, 옆 고정쇠, 표시등, 플라스크 3개, 호스 2개."""
from narang_common import catmull, lathe, replace_object, rounded_box, tube

PACK_Y = 0.172
BACK = 0.215
FLASK_X, FLASK_Y = 0.097, 0.232
TUBE_X, TUBE_Y = -0.009, 0.245
ERLEN_X, ERLEN_Y = -0.11, 0.245


def add(name, builder, material, subsurf=1, mirror=False):
    replace_object(name, builder.to_mesh(name), material, mirror=mirror, subsurf=subsurf)


def build_pack():
    plate = rounded_box((0, PACK_Y, 0.328), (0.1365, 0.043, 0.135), n=4.5, level=6)
    plate.cut_half()
    add("NR_Pack", plate, "NR_White", subsurf=2, mirror=True)
    add("NR_Pack_Clip", rounded_box((0.148, 0.17, 0.358), (0.012, 0.0225, 0.038)), "NR_Gray", mirror=True)

    add("NR_Pack_LED_Cyan", rounded_box((0.053, BACK, 0.42), (0.0125, 0.006, 0.006)), "NR_Cyan")
    add("NR_Pack_LED_Red", rounded_box((-0.053, BACK, 0.42), (0.0068, 0.005, 0.0068), n=2.2), "NR_Red")
    add("NR_Pack_LED_Green", rounded_box((-0.077, BACK, 0.42), (0.0068, 0.005, 0.0068), n=2.2), "NR_Green")

    add("NR_Flask_Glass", lathe([
        (0.012, 0.219), (0.035, 0.228), (0.048, 0.25), (0.0515, 0.272), (0.047, 0.295), (0.033, 0.312),
        (0.017, 0.322), (0.014, 0.335), (0.014, 0.385), (0.02, 0.39), (0.02, 0.397),
    ], FLASK_X, FLASK_Y), "NR_Glass")
    add("NR_Flask_Liquid", lathe([
        (0.010, 0.225), (0.033, 0.231), (0.045, 0.25), (0.0475, 0.272), (0.046, 0.285),
    ], FLASK_X, FLASK_Y), "NR_Blue")

    add("NR_Tube_Glass", lathe([
        (0.012, 0.21), (0.022, 0.216), (0.0245, 0.23), (0.0245, 0.392), (0.028, 0.396), (0.028, 0.40),
    ], TUBE_X, TUBE_Y), "NR_Glass")
    add("NR_Tube_Liquid", lathe([
        (0.008, 0.216), (0.018, 0.221), (0.021, 0.232), (0.021, 0.37),
    ], TUBE_X, TUBE_Y), "NR_Cyan")
    add("NR_Tube_Cap", lathe([(0.021, 0.395), (0.022, 0.40), (0.022, 0.414), (0.021, 0.418)], TUBE_X, TUBE_Y), "NR_Dark")
    add("NR_Tube_Connector", lathe([(0.011, 0.415), (0.011, 0.468)], TUBE_X, TUBE_Y), "NR_Green")

    add("NR_Erlen_Glass", lathe([
        (0.04, 0.226), (0.053, 0.228), (0.055, 0.233), (0.02, 0.325), (0.017, 0.335),
        (0.017, 0.383), (0.021, 0.388), (0.021, 0.392),
    ], ERLEN_X, ERLEN_Y), "NR_Glass")
    add("NR_Erlen_Liquid", lathe([
        (0.04, 0.232), (0.049, 0.236), (0.031, 0.288),
    ], ERLEN_X, ERLEN_Y), "NR_Green")

    add("NR_Clamp_Flask", rounded_box((FLASK_X, 0.238, 0.345), (0.029, 0.03, 0.0155)), "NR_Gray")
    add("NR_Clamp_Tube", rounded_box((TUBE_X, 0.242, 0.342), (0.037, 0.034, 0.0195)), "NR_Gray")
    add("NR_Clamp_Erlen", rounded_box((ERLEN_X, 0.242, 0.345), (0.028, 0.03, 0.0155)), "NR_Gray")
    add("NR_Flask_Cap", lathe([(0.024, 0.39), (0.025, 0.395), (0.024, 0.402)], FLASK_X, FLASK_Y), "NR_Navy")
    add("NR_Erlen_Cap", lathe([(0.025, 0.388), (0.026, 0.393), (0.025, 0.40)], ERLEN_X, ERLEN_Y), "NR_Tan")

    blue = catmull([(0.095, 0.232, 0.395), (0.1235, 0.24, 0.471), (0.104, 0.235, 0.514),
                    (0.057, 0.225, 0.531), (0.01, 0.235, 0.509), (-0.009, 0.245, 0.465)], 6)
    add("NR_Hose_Blue", tube(blue, 0.0085), "NR_HoseBlue")
    green = catmull([(-0.11, 0.245, 0.395), (-0.113, 0.245, 0.458), (-0.1, 0.24, 0.497),
                     (-0.071, 0.23, 0.512), (-0.041, 0.215, 0.494), (-0.036, 0.19, 0.455)], 6)
    add("NR_Hose_Green", tube(green, 0.0085), "NR_HoseGreen")
