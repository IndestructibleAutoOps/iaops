import yaml

from indestructibleautoops.verifier import load_jsonschema


def test_pipeline_schema_loads():
    schema = load_jsonschema("schemas/pipeline.schema.json")
    assert schema.schema["type"] == "object"


def test_pipeline_config_validates():
    data = yaml.safe_load(
        open("configs/indestructibleautoops.pipeline.yaml", encoding="utf-8").read()
    )
    schema = load_jsonschema("schemas/pipeline.schema.json")
    schema.validate(data)
