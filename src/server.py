
from flask import Flask, jsonify
from csv_processor import load_csv, transform_data
from visualizer_stub import generate_artifact_stub
import os

app = Flask(__name__)
CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/BCAzureUsage 1.csv")

@app.route('/api/report', methods=['GET'])
def generate_report():
    try:
        df = load_csv(CSV_PATH)
        summary = transform_data(df)
        artifact = generate_artifact_stub(summary.to_dict())
        return jsonify(artifact)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
