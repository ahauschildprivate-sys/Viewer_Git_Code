
from typing import List

def assign_panel_image_names(steps, points):
    """
    Assigns panel/image names to LES points.
    Each image is named using a combination of Panel and Image.
    Points without an image are assigned to the next available image number.
    """
    panel_image_names = {}
    image_usage = {}
    next_image_id = 1

    for panel_index, step in enumerate(steps, start=1):
        img = step.image
        if img not in image_usage:
            image_usage[img] = []
        image_usage[img].append(panel_index)

    for img, panels in image_usage.items():
        for panel in panels:
            name = f"Panel {panel} Image {img}"
            panel_image_names[(panel, img)] = name

    for pt in points:
        img = pt.image if pt.image else None
        if img is None:
            while next_image_id in image_usage:
                next_image_id += 1
            img = next_image_id
            pt.image = img
            image_usage[img] = [1]
            panel_image_names[(1, img)] = f"Panel 1 Image {img}"
        panel_list = image_usage.get(img, [1])
        panel = panel_list[0]
        pt.panel_image_name = panel_image_names.get((panel, img), f"Panel {panel} Image {img}")
    