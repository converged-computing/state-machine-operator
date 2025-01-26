state_machine_config_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://github.com/converged-computing/state-machine-operator/tree/main/python/state_machine_operator/schema.py",
    "title": "state-machine-workflow-01",
    "description": "State Machine Manager Config",
    "type": "object",
    # The only required thing is jobs
    "required": ["jobs", "workflow"],
    "properties": {
        "jobs": {"$ref": "#/definitions/jobs"},
        "workflow": {"$ref": "#/definitions/workflow"},
        "cluster": {"$ref": "#/definitions/cluster"},
        "logging": {"$ref": "#/definitions/logging"},
        "config_dir": {"type": "string"},
        "additionalProperties": False,
    },
    "definitions": {
        "workflow": {
            "type": "object",
            "required": ["completed"],
            "properties": {
                "completed": {"type": "number", "default": 4},
            },
            "additionalProperties": False,
        },
        "cluster": {
            "type": "object",
            "properties": {
                "max_size": {"type": "number", "default": 6},
                "autoscale": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "logging": {
            "type": "object",
            "properties": {
                "debug": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
        "jobs": {
            "type": ["array"],
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                },
                "required": ["config"],
            },
        },
    },
}

state_machine_job_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://github.com/converged-computing/state-machine-operator/tree/main/python/state_machine_operator/schema.py",
    "title": "state-machine-job-01",
    "description": "State Machine Job Config",
    "type": "object",
    "required": ["name", "config", "script", "image"],
    "properties": {
        "name": {"type": "string"},
        "config": {"$ref": "#/definitions/config"},
        "script": {"type": "string"},
        "image": {"type": "string"},
        "additionalProperties": False,
    },
    "definitions": {
        "config": {
            "type": "object",
            "properties": {
                "nnodes": {"type": "number", "default": 1},
            },
        }
    },
}
