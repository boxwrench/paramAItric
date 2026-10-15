"""Fixed evaluation scripts for SolidCraft's public commands, not product recipes."""

def command(command_id: str, **params) -> dict:
    return {"command": command_id, "params": params}


def parameters(values: dict) -> list[dict]:
    return [command("parameters.change", name=name, expression=f"{value} mm") for name, value in values.items()]


PLATE = {"width": 80, "height": 60, "thickness": 5, "hole_diameter": 10}
BRACKET = {"width": 50, "height": 80, "thickness": 5, "leg": 5}


def plate_stages() -> list[list[dict]]:
    return [parameters(PLATE) + [
        command("sketch.create", plane="XY", name="PlateSketch"),
        command("sketch.draw.dimensioned", command="sketch.rectangle.two_point",
                params={"p0": [0, 0], "p1": [80, 60]}, dimensions={"width": "width", "height": "height"}),
        command("sketch.finish"),
        command("solid.extrude", distance="thickness", operation="new", name="Base", body_name="Plate"),
    ], [
        command("sketch.create", plane="XY", name="BoreSketch"),
        command("sketch.draw.dimensioned", command="sketch.circle.center",
                params={"center": [40, 30], "diameter": 10}, dimensions={"diameter": "hole_diameter"}),
        command("sketch.dimension", entities=["origin", "c1.center"], type="horizontal", value="width/2"),
        command("sketch.dimension", entities=["origin", "c1.center"], type="vertical", value="height/2"),
        command("sketch.finish"),
        command("solid.extrude", distance="thickness", operation="cut", targets=["Plate"], name="Bore"),
    ]]


def bracket_stages() -> list[list[dict]]:
    stage = parameters(BRACKET) + [
        command("sketch.create", plane="XY", name="LProfile"),
        command("sketch.line", points=[[0, 0], [50, 0], [50, 5], [5, 5], [5, 80], [0, 80]], closed=True, infer=True),
    ]
    for entity, expression in (("l1", "width"), ("l2", "leg"), ("l5", "leg"), ("l6", "height")):
        stage.append(command("sketch.dimension", entities=[entity], type="length", value=expression))
    return [stage + [command("sketch.finish"), command("solid.extrude", distance="thickness", operation="new",
                                                    name="LExtrude", body_name="Bracket")]]
