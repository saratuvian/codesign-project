import os
from flask import Flask, jsonify
from dotenv import load_dotenv

from aps_service import (
    get_aps_token,
    create_bucket_if_needed,
    upload_file_signed_s3,
    get_signed_s3_download_url,
    get_object_details,
    to_base64_urn, 
    translate_to_viewer,
    get_manifest,
    get_viewer_token
)

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APS_BUCKET_KEY = os.getenv("APS_BUCKET_KEY")

app = Flask(__name__)


@app.route("/api/token", methods=["GET"])
def api_token():
    """
    Check that APS auth works.
    """
    try:
        token = get_aps_token()
        return jsonify(
            {
                "message": "APS token retrieved successfully",
                "token_type": token.get("token_type"),
                "expires_in": token.get("expires_in"),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/oss/setup", methods=["POST"])
def api_oss_setup():
    """
    Create the OSS bucket (if needed).
    """
    try:
        result = create_bucket_if_needed()
        return jsonify(
            {
                "message": "Bucket created or already exists",
                "status": result["status"],
                "aps_bucket_key": APS_BUCKET_KEY,
                "raw": result["data"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/oss/upload-sample", methods=["POST"])
def api_upload_sample():
    """
    Upload the local DWG example to the bucket.
    """
    try:
        sample_path = os.path.join(BASE_DIR, "samples", "sample.dwg")
        if not os.path.exists(sample_path):
            return jsonify({"error": f"Sample file not found at {sample_path}"}), 400

        result = upload_file_signed_s3(sample_path, "sample.dwg")
        return jsonify(
            {
                "message": "sample.dwg uploaded successfully",
                "aps_bucket_key": APS_BUCKET_KEY,
                "result": result,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/oss/download-sample", methods=["GET"])
def api_download_sample():
    """
    Generate a signed S3 download URL for sample.dwg
    """
    try:
        signed = get_signed_s3_download_url("sample.dwg", minutes_expiration=10)
        return jsonify(
            {
                "message": "Signed download URL generated",
                "object_name": "sample.dwg",
                "signed": signed,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/oss/sample-urn", methods=["GET"])
def api_sample_urn():
    """
    Return objectId and base64 URN for sample.dwg
    """
    try:
        details = get_object_details("sample.dwg")
        object_id = details.get("objectId")
        if not object_id:
            return jsonify({"error": "objectId not found in details", "details": details}), 500

        urn_encoded = to_base64_urn(object_id)
        return jsonify({
            "object_name": "sample.dwg",
            "objectId": object_id,
            "urnEncoded": urn_encoded,
            "details": details
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/viewer/translate-sample", methods=["POST"])
def api_translate_sample():
    """
    Start Model Derivative translation for sample.dwg
    """
    try:
        details = get_object_details("sample.dwg")
        object_id = details.get("objectId")
        urn_encoded = to_base64_urn(object_id)

        result = translate_to_viewer(urn_encoded)

        return jsonify({
            "message": "Translation job submitted",
            "urnEncoded": urn_encoded,
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/viewer/manifest-sample", methods=["GET"])
def api_manifest_sample():
    """
    Check translation status for sample.dwg
    """
    try:
        details = get_object_details("sample.dwg")
        object_id = details.get("objectId")
        urn_encoded = to_base64_urn(object_id)

        manifest = get_manifest(urn_encoded)
        return jsonify({
            "message": "Manifest retrieved",
            "urnEncoded": urn_encoded,
            "status": manifest.get("status"),
            "manifest": manifest
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/viewer/token", methods=["GET"])
def api_viewer_token():
    try:
        token = get_viewer_token()
        return jsonify({
            "access_token": token.get("access_token"),
            "expires_in": token.get("expires_in"),
            "token_type": token.get("token_type"),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/viewer")
def viewer_page():
    return app.send_static_file("viewer.html")


if __name__ == "__main__":
    app.run(debug=True)
