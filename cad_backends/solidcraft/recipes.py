"""Two reviewed SolidCraft command plans; units mm, lower-left XY datum."""

def command(command_id: str, **params) -> dict:
    return {"command": command_id, "params": params}


def parameters(values: dict) -> list[dict]:
    return [command("parameters.change", name=name, expression=f"{value} mm") for name, value in values.items()]


PLATE = {"width": 80, "height": 60, "thickness": 5, "hole_diameter": 10}
BRACKET = {"width": 50, "height": 80, "thickness": 5, "leg": 5}


def plate_stages(p=None) -> list[list[dict]]:
    p = dict(PLATE if p is None else p)
    return [parameters(p) + [
        command("sketch.create", plane="XY", name="PlateSketch"),
        command("sketch.draw.dimensioned", command="sketch.rectangle.two_point",
                params={"p0": [0, 0], "p1": [p["width"], p["height"]]}, dimensions={"width": "width", "height": "height"}),
        command("sketch.finish"),
        command("solid.extrude", distance="thickness", operation="new", name="Base", body_name="Plate"),
    ], [
        command("sketch.create", plane="XY", name="BoreSketch"),
        command("sketch.draw.dimensioned", command="sketch.circle.center",
                params={"center": [p["width"] / 2, p["height"] / 2], "diameter": p["hole_diameter"]}, dimensions={"diameter": "hole_diameter"}),
        command("sketch.dimension", entities=["origin", "c1.center"], type="horizontal", value="width/2"),
        command("sketch.dimension", entities=["origin", "c1.center"], type="vertical", value="height/2"),
        command("sketch.finish"),
        command("solid.extrude", distance="thickness", operation="cut", targets=["Plate"], name="Bore"),
    ]]


def bracket_stages(p=None) -> list[list[dict]]:
    p = dict(BRACKET if p is None else p)
    w, h, leg = (p[k] for k in ("width", "height", "leg"))
    stage = parameters(p) + [
        command("sketch.create", plane="XY", name="LProfile"),
        command("sketch.line", points=[[0, 0], [w, 0], [w, leg], [leg, leg], [leg, h], [0, h]], closed=True, infer=True),
    ]
    for entity, expression in (("l1", "width"), ("l2", "leg"), ("l5", "leg"), ("l6", "height")):
        stage.append(command("sketch.dimension", entities=[entity], type="length", value=expression))
    return [stage + [command("sketch.finish"), command("solid.extrude", distance="thickness", operation="new",
                                                    name="LExtrude", body_name="Bracket")]]
