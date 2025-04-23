
def generate_artifact_stub(summary_data: dict) -> dict:
    # Simulated Claude Artifact structure
    return {
        "type": "artifact.visual.dashboard",
        "title": "Azure Usage Summary",
        "data": summary_data
    }
