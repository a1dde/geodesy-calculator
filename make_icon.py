from __future__ import annotations

from PIL import Image, ImageDraw


def main() -> None:
    # Create 64x64 pixel-art Earth with transparency.
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Palette
    ocean = (20, 80, 170, 255)
    ocean_dark = (10, 55, 130, 255)
    land1 = (40, 170, 90, 255)
    land2 = (30, 135, 70, 255)
    cloud = (240, 250, 255, 220)
    outline = (10, 30, 70, 255)

    # Earth disk
    bbox = (6, 6, size - 6, size - 6)
    d.ellipse(bbox, fill=ocean, outline=outline, width=2)

    # Terminator shading (darker on the left)
    mask = Image.new("L", (size, size), 0)
    dm = ImageDraw.Draw(mask)
    dm.ellipse((4, 6, size - 8, size - 6), fill=180)
    shade_img = Image.new("RGBA", (size, size), ocean_dark)
    img.paste(shade_img, (0, 0), mask)

    # Chunky continents
    for pts, col in [
        ([(30, 20), (34, 18), (38, 20), (40, 24), (38, 28), (34, 30), (30, 28), (28, 24)], land1),
        ([(20, 30), (24, 28), (28, 30), (30, 34), (28, 38), (24, 40), (20, 38), (18, 34)], land2),
        ([(38, 34), (44, 32), (48, 36), (46, 42), (40, 44), (36, 40)], land1),
        ([(26, 44), (30, 42), (34, 44), (36, 48), (32, 52), (26, 50), (24, 46)], land2),
    ]:
        d.polygon(pts, fill=col)

    # Clouds
    for x, y, r in [(22, 22, 4), (44, 22, 5), (18, 42, 5), (44, 46, 4)]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=cloud)

    img.save("earth_pixel.png")
    img.save(
        "earth_pixel.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)],
    )


if __name__ == "__main__":
    main()
